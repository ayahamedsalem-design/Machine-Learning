
import os
import re
import time
import uuid
import logging
import chromadb
from rank_bm25 import BM25Okapi

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
logger = logging.getLogger("Global_Hybrid_RAG")

logger.info("Initializing Global Hybrid RAG System...")
client_ai = initialize_api()

# Unified persistent ChromaDB collection for Global Hybrid RAG
chroma_client = chromadb.PersistentClient(path="./chroma_db_global")
global_hybrid_col = chroma_client.get_or_create_collection(name="global_hybrid_collection")

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

# Global runtime cache for the consolidated BM25 index across all documents
GLOBAL_BM25_CACHE = {
    "bm25": None,
    "chunks": [],
    "metadatas": [],
    "doc_count": 0,
}

GLOBAL_SESSION_ID = "global_chat_session"


def bm25_tokenizer(text: str) -> list:
    """Cleans and tokenizes text into lowercase alphanumeric words for BM25."""
    return re.findall(r"\b\w+\b", text.lower())


def refresh_global_bm25():
    """
    Ensures the in-memory BM25 index reflects all chunks currently stored
    in the global ChromaDB collection.
    """
    total_db_docs = global_hybrid_col.count()
    if total_db_docs == 0:
        GLOBAL_BM25_CACHE["bm25"] = None
        GLOBAL_BM25_CACHE["chunks"] = []
        GLOBAL_BM25_CACHE["metadatas"] = []
        GLOBAL_BM25_CACHE["doc_count"] = 0
        return

    # Rebuild BM25 only if cache is empty or new documents were added to ChromaDB
    if GLOBAL_BM25_CACHE["bm25"] is None or GLOBAL_BM25_CACHE["doc_count"] != total_db_docs:
        logger.info(f"Building consolidated BM25 index for {total_db_docs} chunks from Global DB...")
        db_records = global_hybrid_col.get(include=["documents", "metadatas"])
        all_chunks = db_records.get("documents", [])
        all_metadatas = db_records.get("metadatas", [])

        tokenized_corpus = [bm25_tokenizer(chunk) for chunk in all_chunks]
        GLOBAL_BM25_CACHE["bm25"] = BM25Okapi(tokenized_corpus)
        GLOBAL_BM25_CACHE["chunks"] = all_chunks
        GLOBAL_BM25_CACHE["metadatas"] = all_metadatas
        GLOBAL_BM25_CACHE["doc_count"] = total_db_docs
        logger.info("Consolidated BM25 index built successfully.")


# ==========================================
# 2. Indexing (Feed Global DB Once per File)
# ==========================================

def initialize_hybrid_index(pdf_source):
    """
    Indexes a PDF document into the global hybrid collection and refreshes the BM25 index.
    Skips indexing if the file already exists in the database.
    """
    file_name = resolve_file_name(pdf_source)
    logger.info(f"--- Checking Global Hybrid DB for '{file_name}' ---")

    # Check if file is already indexed in the Global DB
    existing_docs = global_hybrid_col.get(where={"source": file_name}, limit=1)
    if existing_docs and existing_docs.get("ids") and len(existing_docs["ids"]) > 0:
        logger.info(f"Document '{file_name}' is already indexed in Global Hybrid DB. Skipping.")
        refresh_global_bm25()
        return

    # Extract and split text using the shared utility
    logger.info(f"Starting Extraction & Standard Chunking for '{file_name}'...")
    chunks, metadatas = extract_and_chunk_standard(
        pdf_source, chunk_size=1000, chunk_overlap=200
    )

    if not chunks:
        logger.warning(f"No valid chunks extracted from '{file_name}'.")
        return

    # Generate dense embeddings in batches with retry logic
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

        time.sleep(1)

    # Save to Global Hybrid Collection with unique UUIDs
    chunk_ids = [f"hybrid_{uuid.uuid4().hex[:8]}" for _ in range(len(chunks))]
    global_hybrid_col.add(
        documents=chunks,
        embeddings=embeddings_list,
        metadatas=metadatas,
        ids=chunk_ids,
    )
    logger.info(f"Successfully added {len(chunks)} chunks from '{file_name}' to Global Hybrid DB.")

    # Refresh global BM25 cache to include the newly added chunks
    refresh_global_bm25()


# ==========================================
# 3. Querying (Global Multi-Question Hybrid Search)
# ==========================================

def retrieve_hybrid_context(user_query: str, top_k: int = 6):
    """
    Performs Hybrid Retrieval (Dense Vector + Sparse BM25 via RRF) across ALL indexed documents
    for each sub-question in the user query.
    """
    refresh_global_bm25()
    bm25 = GLOBAL_BM25_CACHE["bm25"]
    chunks = GLOBAL_BM25_CACHE["chunks"]
    metadatas = GLOBAL_BM25_CACHE["metadatas"]

    sub_queries = decompose_multi_questions(user_query)
    consolidated_scores = {}
    rrf_k = 60
    t_chunks_limit = min(10, len(chunks))

    for idx, sub_q in enumerate(sub_queries, start=1):
        logger.debug(f"Running Hybrid Retrieval for sub-query #{idx}: '{sub_q}'")

        # Step A: Dense Semantic Search
        dense_chunks = []
        try:
            query_vec = client_ai.embeddings.create(
                model=EMBEDDING_MODEL,
                input=[sub_q],
            ).data[0].embedding

            dense_results = global_hybrid_col.query(
                query_embeddings=[query_vec],
                n_results=t_chunks_limit,
                include=["documents"],
            )
            if dense_results.get("documents") and dense_results["documents"]:
                dense_chunks = dense_results["documents"][0]
        except Exception as e:
            logger.error(f"Dense search failed for sub-query '{sub_q}': {e}", exc_info=True)

        # Step B: Sparse BM25 Keyword Search
        tokenized_q = bm25_tokenizer(sub_q)
        sparse_chunks = bm25.get_top_n(tokenized_q, chunks, n=t_chunks_limit)

        # Step C: Reciprocal Rank Fusion (RRF) for this branch
        for rank, doc in enumerate(dense_chunks):
            consolidated_scores[doc] = consolidated_scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))

        for rank, doc in enumerate(sparse_chunks):
            consolidated_scores[doc] = consolidated_scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Rank all retrieved documents across all sub-queries by combined RRF score
    ranked_docs = sorted(consolidated_scores.items(), key=lambda item: item[1], reverse=True)
    top_chunks = [doc for doc, _ in ranked_docs[:top_k]]
    logger.info(f"RRF selected top {len(top_chunks)} unique context chunks across all sub-queries.")

    # Map chunks to their source filename and page number
    chunk_to_meta = {c: m for c, m in zip(chunks, metadatas)}
    formatted_contexts = []

    for doc in top_chunks:
        meta_info = chunk_to_meta.get(doc, {})
        source_file = meta_info.get("source", "Unknown_File") if isinstance(meta_info, dict) else "Unknown_File"
        page_num = meta_info.get("page", "?") if isinstance(meta_info, dict) else "?"
        formatted_contexts.append(f"[Source: {source_file} | Page: {page_num}]:\n{doc}")

    full_context_text = "\n\n---\n\n".join(formatted_contexts)
    return full_context_text, formatted_contexts


def run_hybrid_chat_session(user_query: str, top_k: int = 6, history_limit: int = 5):
    """
    Searches across ALL indexed documents using Hybrid RAG (Dense + BM25),
    supports multi-questions, and maintains a rolling window of chat history.
    """
    logger.info("=== Starting Global Multi-Query Hybrid RAG ===")
    logger.info(f"User Query: '{user_query}'")

    if global_hybrid_col.count() == 0:
        logger.error("Global Hybrid DB is empty. Please upload and index documents first.")
        return "The database is empty. Please upload and index some PDFs first.", []

    # 1. Retrieve consolidated hybrid context
    full_context_text, formatted_contexts = retrieve_hybrid_context(user_query, top_k=top_k)

    # 2. Load rolling window history
    logger.info("Loading global conversation history...")
    global_history = load_file_history(GLOBAL_SESSION_ID)
    recent_history = (
        global_history[-history_limit:] if len(global_history) > history_limit else global_history
    )
    logger.info(f"Using {len(recent_history)} recent turns from history (Total saved: {len(global_history)}).")

    # 3. Build prompt and invoke LLM
    current_turn_prompt = f"""[Context from Global Database]:
{full_context_text}

[User Question(s)]:
{user_query}
"""

    messages_to_send = [{"role": "system", "content": SYS_PROMPT}]
    for item in recent_history:
        messages_to_send.append({"role": "user", "content": item["query"]})
        messages_to_send.append({"role": "assistant", "content": item["answer"]})

    messages_to_send.append({"role": "user", "content": current_turn_prompt})

    logger.info("Invoking LLM 'nvidia/nemotron-3.5-lightning:free'...")
    try:
        completion = client_ai.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages_to_send,
            temperature=0.2,
        )
        assistant_reply = completion.choices[0].message.content
        logger.info("LLM global response generated successfully.")
    except Exception as e:
        logger.critical(f"LLM generation failed: {e}", exc_info=True)
        raise e

    # 4. Persist chat history
    persist_chat_history(GLOBAL_SESSION_ID, user_query, assistant_reply, full_context_text)
    return assistant_reply, formatted_contexts


if __name__ == "__main__":
    # 1. Index a PDF once into Global Hybrid DB:
    # sample_pdf = r"D:\GitProjects\Machine-Learning\Docs\Advice For Risk Associated with Cultured Meat.pdf"
    # initialize_hybrid_index(sample_pdf)

    # 2. Query across all indexed PDFs:
    sample_query = """1. What are the general steps in cultured meat production?
2. Why is Mycoplasma contamination difficult to detect visually?"""

    answer, contexts = run_hybrid_chat_session(sample_query)
    print("\n--- Final Answer ---\n", answer)