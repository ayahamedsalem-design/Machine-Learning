
import math
import os
import time
import logging
import chromadb
try:       
    from RAGs.logger_config import setup_logging
    from RAGs.chat_history import persist_chat_history, load_file_history
    from RAGs.extract_and_chunk_pdf import (
        initialize_api, 
        resolve_file_name, 
        decompose_multi_questions,
        extract_and_chunk_hierarchical,
        SYS_PROMPT
    )
except ModuleNotFoundError:
    from logger_config import setup_logging
    from chat_history import persist_chat_history, load_file_history
    from extract_and_chunk_pdf import (
        initialize_api, 
        resolve_file_name, 
        decompose_multi_questions,
        extract_and_chunk_hierarchical,
        SYS_PROMPT
    )

# ==========================================
# 1. Setup & Configuration
# ==========================================

setup_logging()

logger = logging.getLogger(__name__)

logger.info("Initializing OpenRouter API Client for Parent-Child RAG...")


client_ai = initialize_api()

# Unified persistent ChromaDB collections for Global Hierarchical RAG
chroma_client = chromadb.PersistentClient(path="./chroma_db_global")
global_child_col = chroma_client.get_or_create_collection(name="global_child_collection")
global_parent_col = chroma_client.get_or_create_collection(name="global_parent_collection")

GLOBAL_SESSION_ID = "global_chat_session"

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

# ==========================================
# 2. Indexing (Feed Global DB Once per File)
# ==========================================

def index_parent_child_rag(pdf_source):
    """
    Indexes a PDF document into the global parent and child collections.
    Skips indexing if the file already exists in the database.
    """
    file_name = resolve_file_name(pdf_source)
    logger.info(f"--- Checking Global Hierarchical DB for '{file_name}' ---")

    # Check if file is already indexed via child metadata
    existing_docs = global_child_col.get(where={"source": file_name}, limit=1)
    if existing_docs and existing_docs.get("ids") and len(existing_docs["ids"]) > 0:
        logger.info(f"Document '{file_name}' is already indexed in Global Hierarchical DB. Skipping.")
        return

    # Extract and split into hierarchical chunks using shared utility
    logger.info(f"Starting Hierarchical Extraction & Chunking for '{file_name}'...")
    parent_texts, parent_ids, child_chunks, child_metadatas, child_ids = (
        extract_and_chunk_hierarchical(
            pdf_source,
            parent_chunk_words=300,
            child_chunk_words=70,
            child_overlap=15,
        )
    )

    if not child_chunks or not parent_texts:
        logger.warning(f"No valid chunks extracted from '{file_name}'.")
        return

    # Store parent documents with source metadata
    parent_metadatas = [{"source": file_name} for _ in parent_texts]
    logger.info(f"Saving {len(parent_texts)} parent blocks to Global Parent DB...")
    global_parent_col.add(
        documents=parent_texts,
        metadatas=parent_metadatas,
        ids=parent_ids,
    )

    # Generate embeddings for child chunks in batches with retry logic
    child_embeddings = []
    batch_size = 15
    total_batches = math.ceil(len(child_chunks) / batch_size)
    logger.info(f"Generating embeddings for {len(child_chunks)} child chunks in {total_batches} batches...")

    for idx, i in enumerate(range(0, len(child_chunks), batch_size), start=1):
        batch = child_chunks[i : i + batch_size]
        success = False

        for attempt in range(3):
            try:
                response = client_ai.embeddings.create(
                    model=EMBEDDING_MODEL,
                    input=batch,
                )
                child_embeddings.extend([item.embedding for item in response.data])
                success = True
                time.sleep(3)
                break
            except Exception as e:
                logger.warning(f"Batch {idx} attempt {attempt + 1} failed: {e}. Retrying in 2s...")
                time.sleep(2)

        if not success:
            logger.error(f"Failed to generate embeddings for batch {idx}. Halting indexing.")
            raise RuntimeError("Embeddings service failed to respond.")

        time.sleep(1)

    # Save child chunks and embeddings
    global_child_col.add(
        documents=child_chunks,
        embeddings=child_embeddings,
        metadatas=child_metadatas,
        ids=child_ids,
    )
    logger.info(f"Successfully indexed '{file_name}' into Global Parent-Child DB.")


# ==========================================
# 3. Querying (Global Multi-Question Search)
# ==========================================

def run_parent_child_chunking_RAG(user_query, max_parents=6, history_limit=5):
    """
    Searches across ALL indexed documents using child embeddings, retrieves unique parent contexts,
    supports multi-questions, and maintains a rolling window of chat history.
    """
    logger.info("=== Starting Global Multi-Query Parent-Child RAG ===")
    logger.info(f"User Query: '{user_query}'")

    if global_child_col.count() == 0 or global_parent_col.count() == 0:
        logger.error("Global Hierarchical DB is empty. Please upload and index documents first.")
        return "The database is empty. Please upload and index some PDFs first.", []

    # 1. Decompose query and retrieve matching parent IDs across all sub-queries
    sub_queries = decompose_multi_questions(user_query)
    matched_parent_ids = []

    for idx, sub_q in enumerate(sub_queries, start=1):
        logger.debug(f"Searching children for sub-query #{idx}: '{sub_q}'")
        try:
            query_resp = client_ai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[sub_q],
            )
            query_vec = query_resp.data[0].embedding

            search_results = global_child_col.query(
                query_embeddings=[query_vec],
                n_results=10,
                include=["metadatas"],
            )

            if search_results.get("metadatas") and search_results["metadatas"]:
                for meta in search_results["metadatas"][0]:
                    pid = meta.get("parent_id")
                    if pid and pid not in matched_parent_ids:
                        matched_parent_ids.append(pid)
        except Exception as e:
            logger.error(f"Child search failed for sub-query '{sub_q}': {e}", exc_info=True)

    # 2. Fetch unique parent documents with their source filenames
    top_unique_parents = matched_parent_ids[:max_parents]
    logger.info(f"Selected {len(top_unique_parents)} unique parent IDs across all sub-queries.")

    if not top_unique_parents:
        return "No relevant context found in the indexed documents.", []

    parent_records = global_parent_col.get(
        ids=top_unique_parents,
        include=["documents", "metadatas"],
    )

    formatted_contexts = []
    docs = parent_records.get("documents", [])
    metas = parent_records.get("metadatas", [])

    for doc, meta in zip(docs, metas):
        source_file = meta.get("source", "Unknown_File") if isinstance(meta, dict) else "Unknown_File"
        formatted_contexts.append(f":\n{doc}")

    full_context_text = "\n\n---\n\n".join(formatted_contexts)

    # 3. Load rolling window history
    logger.info("Loading global conversation history...")
    global_history = load_file_history(GLOBAL_SESSION_ID)
    recent_history = (
        global_history[-history_limit:] if len(global_history) > history_limit else global_history
    )
    logger.info(f"Using {len(recent_history)} recent turns from history (Total saved: {len(global_history)}).")

    # 4. Build prompt and invoke LLM
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

    logger.info("Invoking LLM 'nvidia/nemotron-3.5-super-vl:free'...")
    try:
        completion = client_ai.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages_to_send,
        )
        assistant_reply = completion.choices[0].message.content
        logger.info("LLM response generated successfully.")
    except Exception as e:
        logger.critical(f"LLM generation failed: {e}", exc_info=True)
        raise e

    # 5. Persist chat history
    persist_chat_history(GLOBAL_SESSION_ID, user_query, assistant_reply, full_context_text)
    return assistant_reply, formatted_contexts


if __name__ == "__main__":
    # Example usage:
    # sample_pdf = r"D:\GitProjects\Machine-Learning\Docs\Advice For Risk Associated with Cultured Meat.pdf"
    # index_parent_child_rag(sample_pdf)

    sample_query = """1. What are the general steps in cultured meat production?
2. Why is Mycoplasma contamination difficult to detect visually?"""

    answer, contexts = run_parent_child_chunking_RAG(sample_query)
    print("\n--- Final Answer ---\n", answer)