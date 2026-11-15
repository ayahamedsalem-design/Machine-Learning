import os
import re
import logging

try:
    from RAGs.logger_config import setup_logging
    from RAGs.chat_history import persist_chat_history, load_file_history
    from RAGs.extract_and_chunk_pdf import initialize_api, decompose_multi_questions, SYS_PROMPT
    from RAGs.hybrid_RAG import (
        refresh_global_bm25,
        GLOBAL_BM25_CACHE,
        bm25_tokenizer,
        global_hybrid_col
    )
except ModuleNotFoundError:
    from logger_config import setup_logging
    from chat_history import persist_chat_history, load_file_history
    from extract_and_chunk_pdf import initialize_api, decompose_multi_questions, SYS_PROMPT
    from hybrid_RAG import (
        refresh_global_bm25,
        GLOBAL_BM25_CACHE,
        bm25_tokenizer,
        global_hybrid_col
    )

# ==========================================
# 1. Setup & Configuration
# ==========================================

setup_logging()
logger = logging.getLogger("Global_Corrective_Hybrid_RAG")

logger.info("Initializing OpenRouter API Client for Global Corrective Hybrid RAG...")
client_ai = initialize_api()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

GLOBAL_SESSION_ID = "global_chat_session"

def grade_document(query: str, doc_content: str) -> bool:
    """
    Evaluator: Binary classification (yes/no) to verify if the retrieved hybrid chunk
    contains information relevant to the specific sub-question.
    """
    eval_prompt = f"""You are an objective document evaluator.
Assess whether the provided context snippet contains information relevant to answering the question.

Question:
{query}

Context Snippet:
{doc_content}

Respond strictly with 'yes' if relevant, or 'no' if irrelevant. Do not provide explanations."""

    try:
        response = client_ai.chat.completions.create(
            model=CHAT_MODEL,
            messages=[{"role": "user", "content": eval_prompt}],
            temperature=0.0,
            max_tokens=5,
        )
        decision = response.choices[0].message.content.strip().lower()
        return "yes" in decision
    except Exception as e:
        logger.warning(f"Grading failed ({e}), accepting document as fallback.")
        return True


# ==========================================
# 2. Querying (Global Multi-Question Corrective Hybrid RAG)
# ==========================================

def run_corrective_hybrid_rag(user_query: str, top_k_per_query: int = 4, history_limit: int = 5):
    """
    Searches across ALL indexed documents using Hybrid RAG (Dense + BM25),
    grades each chunk against its triggering sub-question, and generates a cited response.
    """
    logger.info("=== Starting Global Multi-Query Corrective Hybrid RAG ===")
    logger.info(f"User Query: '{user_query}'")

    if global_hybrid_col.count() == 0:
        logger.error("Global Hybrid DB is empty. Please upload and index documents first.")
        return "The database is empty. Please upload and index some PDFs first.", []

    # 1. Update BM25 Cache & Decompose Query
    refresh_global_bm25()
    bm25 = GLOBAL_BM25_CACHE["bm25"]
    chunks = GLOBAL_BM25_CACHE["chunks"]
    metadatas = GLOBAL_BM25_CACHE["metadatas"]

    sub_queries = decompose_multi_questions(user_query)
    
    chunk_to_queries = {}
    ordered_chunks = []
    rrf_k = 60
    t_chunks_limit = min(10, len(chunks))

    # 2. Retrieval Phase (Hybrid RRF per sub-query)
    for idx, sub_q in enumerate(sub_queries, start=1):
        logger.debug(f"Running Hybrid Retrieval for sub-query #{idx}: '{sub_q}'")
        
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

        tokenized_q = bm25_tokenizer(sub_q)
        sparse_chunks = bm25.get_top_n(tokenized_q, chunks, n=t_chunks_limit)

        branch_scores = {}
        for rank, doc in enumerate(dense_chunks):
            branch_scores[doc] = branch_scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))
        for rank, doc in enumerate(sparse_chunks):
            branch_scores[doc] = branch_scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))

        # Sort and take top chunks for this specific sub-query
        ranked_branch_docs = sorted(branch_scores.items(), key=lambda item: item[1], reverse=True)
        top_branch_chunks = [doc for doc, _ in ranked_branch_docs[:top_k_per_query]]

        # Map each retrieved chunk to the sub-queries that found it
        for doc in top_branch_chunks:
            if doc not in chunk_to_queries:
                chunk_to_queries[doc] = []
                ordered_chunks.append(doc)
            chunk_to_queries[doc].append(sub_q)

    logger.info(f"Retrieved {len(ordered_chunks)} unique candidate chunks across all sub-queries.")

    # 3. Corrective Phase (Grading)
    logger.info("--- CRAG: Filtering and Grading Candidate Hybrid Chunks ---")
    verified_formatted_contexts = []
    chunk_to_meta = {c: m for c, m in zip(chunks, metadatas)}

    for doc in ordered_chunks:
        # Keep the chunk if it is relevant to AT LEAST ONE of the sub-queries that triggered it
        is_relevant = any(grade_document(q, doc) for q in chunk_to_queries[doc])
        if is_relevant:
            meta_info = chunk_to_meta.get(doc, {})
            source_file = meta_info.get("source", "Unknown_File") if isinstance(meta_info, dict) else "Unknown_File"
            page_num = meta_info.get("page", "?") if isinstance(meta_info, dict) else "?"
            verified_formatted_contexts.append(f"[Source: {source_file} | Page: {page_num}]:\n{doc}")

    logger.info(f"CRAG Verification: {len(verified_formatted_contexts)}/{len(ordered_chunks)} chunks passed grading.")

    # 4. Context Formulation
    if not verified_formatted_contexts:
        logger.warning("No chunks passed relevance check.")
        full_context_text = "The context does not contain any relevant information for the question."
    else:
        full_context_text = "\n\n---\n\n".join(verified_formatted_contexts)

    # 5. Load Rolling Window History
    logger.info("Loading global conversation history...")
    global_history = load_file_history(GLOBAL_SESSION_ID)
    recent_history = (
        global_history[-history_limit:] if len(global_history) > history_limit else global_history
    )
    logger.info(f"Using {len(recent_history)} recent turns from history (Total saved: {len(global_history)}).")

    # 6. Generation Phase

    current_prompt = f"""[Context from Global Database]:
{full_context_text}

[User Question(s)]:
{user_query}"""

    messages_to_send = [{"role": "system", "content": SYS_PROMPT}]
    for item in recent_history:
        messages_to_send.append({"role": "user", "content": item["query"]})
        messages_to_send.append({"role": "assistant", "content": item["answer"]})

    messages_to_send.append({"role": "user", "content": current_prompt})

    logger.info(f"Sending prompt to generation model '{CHAT_MODEL}'...")
    try:
        completion = client_ai.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages_to_send,
            temperature=0.2,
        )
        assistant_reply = completion.choices[0].message.content
        logger.info("LLM response received successfully.")
    except Exception as e:
        logger.critical(f"LLM generation failed: {e}", exc_info=True)
        raise e

    # 7. Persist Chat History
    logger.info("Saving Q&A session to global history file...")
    persist_chat_history(GLOBAL_SESSION_ID, user_query, assistant_reply, full_context_text)
    logger.info("Global Corrective Hybrid RAG execution completed.")

    return assistant_reply, verified_formatted_contexts