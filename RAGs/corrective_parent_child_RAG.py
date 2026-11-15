import os
import logging
import chromadb

try:
    from RAGs.logger_config import setup_logging
    from RAGs.chat_history import persist_chat_history, load_file_history
    from RAGs.extract_and_chunk_pdf import (
        initialize_api,
        decompose_multi_questions,
        SYS_PROMPT
    )
except ModuleNotFoundError:
    from logger_config import setup_logging
    from chat_history import persist_chat_history, load_file_history
    from extract_and_chunk_pdf import (
        initialize_api,
        decompose_multi_questions,
        SYS_PROMPT
    )

# ==========================================
# 1. Setup & Configuration
# ==========================================

setup_logging()
logger = logging.getLogger("Global_Corrective_Parent_RAG")

logger.info("Initializing OpenRouter API Client for Global Corrective Parent-Child RAG...")
client_ai = initialize_api()

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
CHAT_MODEL = os.getenv("CHAT_MODEL")

# Connect to the shared Global Hierarchical ChromaDB collections
chroma_client = chromadb.PersistentClient(path="./chroma_db_global")
global_child_col = chroma_client.get_or_create_collection(name="global_child_collection")
global_parent_col = chroma_client.get_or_create_collection(name="global_parent_collection")

GLOBAL_SESSION_ID = "global_chat_session"

def grade_parent_document(query: str, doc_content: str) -> bool:
    """
    Evaluator: Binary classification (yes/no) to verify if the retrieved parent
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
# 2. Querying (Global Multi-Question CRAG)
# ==========================================

def run_corrective_parent_child_rag(user_query: str, max_parents_per_query: int = 4, history_limit: int = 5):
    """
    Searches across ALL indexed documents using child embeddings, retrieves parent blocks,
    grades each parent against its triggering sub-question, and generates a cited response.
    """
    logger.info("=== Starting Global Multi-Query Corrective Parent-Child RAG ===")
    logger.info(f"User Query: '{user_query}'")

    if global_child_col.count() == 0 or global_parent_col.count() == 0:
        logger.error("Global Hierarchical DB is empty. Please upload and index documents first.")
        return "The database is empty. Please upload and index some PDFs first.", []

    # 1. Decompose multi-question query and generate batch embeddings
    sub_queries = decompose_multi_questions(user_query)
    try:
        query_resp = client_ai.embeddings.create(
            model=EMBEDDING_MODEL,
            input=sub_queries,
        )
        query_vectors = [item.embedding for item in query_resp.data]
    except Exception as e:
        logger.error(f"Failed to generate embeddings for sub-queries: {e}", exc_info=True)
        raise e

    # 2. Retrieval Phase (Map each candidate parent_id to the sub-queries that retrieved it)
    parent_to_queries = {}
    ordered_parent_ids = []

    for idx, (sub_q, q_vec) in enumerate(zip(sub_queries, query_vectors), start=1):
        logger.debug(f"Searching children for sub-query #{idx}: '{sub_q}'")
        search_results = global_child_col.query(
            query_embeddings=[q_vec],
            n_results=10,
            include=["metadatas"],
        )

        sub_parents = []
        if search_results.get("metadatas") and search_results["metadatas"]:
            for meta in search_results["metadatas"][0]:
                pid = meta.get("parent_id")
                if pid and pid not in sub_parents:
                    sub_parents.append(pid)
                if len(sub_parents) >= max_parents_per_query:
                    break

        for pid in sub_parents:
            if pid not in parent_to_queries:
                parent_to_queries[pid] = []
                ordered_parent_ids.append(pid)
            parent_to_queries[pid].append(sub_q)

    logger.info(f"Retrieved {len(ordered_parent_ids)} unique candidate parent IDs across all sub-queries.")

    # Fetch parent texts and source metadata from Global Parent Collection
    candidate_records = []
    if ordered_parent_ids:
        parent_records = global_parent_col.get(
            ids=ordered_parent_ids,
            include=["documents", "metadatas"],
        )
        doc_map = dict(zip(parent_records["ids"], parent_records["documents"]))
        meta_map = dict(zip(parent_records["ids"], parent_records["metadatas"]))

        for pid in ordered_parent_ids:
            if pid in doc_map:
                candidate_records.append({
                    "id": pid,
                    "text": doc_map[pid],
                    "meta": meta_map.get(pid, {}),
                    "queries": parent_to_queries[pid],
                })

    # 3. Corrective Phase (Grade each parent against the specific sub-queries that triggered it)
    logger.info("--- CRAG: Filtering and Grading Candidate Parent Chunks ---")
    verified_formatted_contexts = []

    for record in candidate_records:
        # Keep parent if it is relevant to at least one of its triggering sub-questions
        is_relevant = any(grade_parent_document(q, record["text"]) for q in record["queries"])
        if is_relevant:
            source_file = (
                record["meta"].get("source", "Unknown_File")
                if isinstance(record["meta"], dict)
                else "Unknown_File"
            )
            verified_formatted_contexts.append(f"[Source: {source_file}]:\n{record['text']}")

    logger.info(
        f"CRAG Verification: {len(verified_formatted_contexts)}/{len(candidate_records)} parents passed grading."
    )

    # 4. Context Formulation
    if not verified_formatted_contexts:
        logger.warning("No parent chunks passed relevance check.")
        full_context_text = "The context does not contain any relevant information for the question."
    else:
        full_context_text = "\n\n---\n\n".join(verified_formatted_contexts)

    # 5. Load Rolling Window History
    logger.info("Loading global conversation history...")
    global_history = load_file_history(GLOBAL_SESSION_ID)
    recent_history = (
        global_history[-history_limit:] if len(global_history) > history_limit else global_history
    )
    logger.info(
        f"Using {len(recent_history)} recent turns from history (Total saved: {len(global_history)})."
    )

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
    logger.info("Global Corrective Parent RAG execution completed.")

    return assistant_reply, verified_formatted_contexts


if __name__ == "__main__":
    sample_query = (
        "1. What are the general steps in cultured meat production? \n"
        "2. Why is Mycoplasma contamination difficult to detect visually?"
    )
    answer, docs = run_corrective_parent_rag(sample_query)
    print("\n" + "=" * 60)
    print("FINAL MODEL ANSWER:")
    print("=" * 60)
    print(answer)