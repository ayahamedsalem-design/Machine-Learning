
import os
import time
import uuid
import logging
import chromadb
import ollama

try:
    from RAGs.logger_config import setup_logging
    from RAGs.chat_history import persist_chat_history, load_file_history
    from RAGs.extract_and_chunk_pdf import (
        initialize_api, 
        resolve_file_name, 
        decompose_multi_questions, 
        extract_and_chunk_standard,
        SYS_PROMPT
    )
except ModuleNotFoundError:
    from logger_config import setup_logging
    from chat_history import persist_chat_history, load_file_history
    from extract_and_chunk_pdf import (
        initialize_api, 
        resolve_file_name, 
        decompose_multi_questions,
        extract_and_chunk_standard,
        SYS_PROMPT
    )

# ==========================================
# 1. Setup & Configuration
# ==========================================

setup_logging()

logger = logging.getLogger(__name__)

logger.info("Initializing OpenRouter API Client for Basic RAG...")

client_ai = initialize_api()

# Unified persistent ChromaDB collection for Global Basic RAG
chroma_client = chromadb.PersistentClient(path="./chroma_db_global")
global_collection = chroma_client.get_or_create_collection(name="global_basic_collection")

# Unified session ID for global chat history
GLOBAL_SESSION_ID = "global_chat_session"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

# ==========================================
# 2. Indexing (Feed Global DB Once per File)
# ==========================================

def index_basic_rag(pdf_source):
    """
    Indexes a PDF document into the global basic collection.
    Skips indexing if the file already exists in the database.
    """
    file_name = resolve_file_name(pdf_source)
    logger.info(f"--- Checking Global Basic DB for '{file_name}' ---")

    # Check if file is already indexed in the Global DB
    existing_docs = global_collection.get(where={"source": file_name}, limit=1)
    if existing_docs and existing_docs.get("ids") and len(existing_docs["ids"]) > 0:
        logger.info(f"Document '{file_name}' is already indexed in Global Basic DB. Skipping.")
        return

    # Extract and split text using the shared utility
    logger.info(f"Starting Extraction & Standard Chunking for '{file_name}'...")
    chunks, metadatas = extract_and_chunk_standard(
        pdf_source, chunk_size=1000, chunk_overlap=200
    )

    if not chunks:
        logger.warning(f"No text extracted from '{file_name}'.")
        return

    # Generate embeddings in batches with retry logic
    embeddings_list = []
    batch_size = 15
    total_batches = (len(chunks) + batch_size - 1) // batch_size
    logger.info(f"Generating embeddings via OpenRouter in {total_batches} batches...")

    for idx, i in enumerate(range(0, len(chunks), batch_size), start=1):
        batch = chunks[i : i + batch_size]
        success = False

        for attempt in range(3):
            try:
                response = client_ai.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                )
                embeddings_list.extend([item.embedding for item in response.data])
                success = True
                time.sleep(3)
                break
            except Exception as e:
                logger.warning(f"Batch {idx} attempt {attempt + 1} failed: {e}. Retrying in 2s...")
                time.sleep(2)

        if not success:
            logger.error(f"Failed to generate embeddings for batch {idx}. Halting indexing.")
            raise RuntimeError("Embeddings service failed to respond.")

    # Save to Global Collection with unique UUIDs
    chunk_ids = [f"basic_{uuid.uuid4().hex[:8]}" for _ in range(len(chunks))]

    global_collection.add(
        documents=chunks,
        embeddings=embeddings_list,
        metadatas=metadatas,
        ids=chunk_ids,
    )
    logger.info(f"Successfully added {len(chunks)} chunks from '{file_name}' to Global Basic DB.")


# ==========================================
# 3. Querying (Global Multi-Question Search)
# ==========================================

def run_basic_RAG(user_query, top_k_per_query=3, history_limit=5):
    """
    Searches across ALL indexed documents using the user query only.
    Supports multi-questions and maintains a rolling window of chat history.
    """
    logger.info("=== Starting Global Multi-Query Basic RAG ===")
    logger.info(f"User Query: '{user_query}'")

    if global_collection.count() == 0:
        logger.error("Global Basic DB is empty. Please upload and index documents first.")
        return "The database is empty. Please upload and index some PDFs first.", []

    # 1. Decompose query and retrieve unique chunks across all sub-queries
    sub_queries = decompose_multi_questions(user_query)
    unique_chunks_dict = {}

    for idx, sub_q in enumerate(sub_queries, start=1):
        logger.debug(f"Retrieving chunks for sub-query #{idx}: '{sub_q}'")
        try:
            query_res = client_ai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[sub_q],
            )
            query_vector = query_res.data[0].embedding

            results = global_collection.query(
                query_embeddings=[query_vector],
                n_results=top_k_per_query,
                include=["documents", "metadatas"],
            )

            if results.get("documents") and results["documents"]:
                docs = results["documents"][0]
                metas = results["metadatas"][0]

                for doc, meta in zip(docs, metas):
                    source_file = meta.get("source", "Unknown_File")
                    page_num = meta.get("page", "?")
                    formatted_chunk = f":\n{doc}"
                    unique_chunks_dict[doc] = formatted_chunk

        except Exception as e:
            logger.error(f"Search failed for sub-query '{sub_q}': {e}", exc_info=True)

    # 2. Consolidate context
    formatted_contexts = list(unique_chunks_dict.values())
    full_context_text = "\n\n---\n\n".join(formatted_contexts)
    logger.info(f"Retrieved {len(formatted_contexts)} unique chunks across all sub-queries.")

    # 3. Load rolling window history
    logger.info("Loading global conversation history...")
    global_history = load_file_history(GLOBAL_SESSION_ID)
    recent_history = (
        global_history[-history_limit:] if len(global_history) > history_limit else global_history
    )
    logger.info(f"Using {len(recent_history)} recent turns from history (Total saved: {len(global_history)}).")

    # 4. Build prompt and invoke local Ollama LLM
    prompt = f"""[Context from Global Database]:
{full_context_text}

[User Question(s)]:
{user_query}
"""

    messages_to_send = [{"role": "system", "content": SYS_PROMPT}]
    for item in recent_history:
        messages_to_send.append({"role": "user", "content": item["query"]})
        messages_to_send.append({"role": "assistant", "content": item["answer"]})

    messages_to_send.append({"role": "user", "content": prompt})

    logger.info("Invoking Ollama 'llama3.2:1b'...")
    try:
        response = ollama.chat(
            model="llama3.2:1b",
            messages=messages_to_send,
            options={
                "temperature": 0.0,
                "top_p": 0.1,
                "num_ctx": 4096,
            },
        )
        assistant_reply = response["message"]["content"]
        logger.info("Ollama global response generated successfully.")
    except Exception as e:
        logger.critical(f"Ollama execution failed: {e}", exc_info=True)
        raise e

    # 5. Persist chat history
    persist_chat_history(GLOBAL_SESSION_ID, user_query, assistant_reply, full_context_text)
    return assistant_reply, formatted_contexts


if __name__ == "__main__":
    # 1. Index a PDF once into Global DB:
    # sample_pdf = r"D:\GitProjects\Machine-Learning\Docs\Advice For Risk Associated with Cultured Meat.pdf"
    # index_basic_rag(sample_pdf)

    # 2. Query across all indexed PDFs:
    sample_query = """1. What are the three general steps in the production process of cultured meat?
2. Why is Mycoplasma contamination difficult to detect visually?"""

    answer, chunks = run_basic_RAG(sample_query)
    print("\n--- Final Answer ---\n", answer)