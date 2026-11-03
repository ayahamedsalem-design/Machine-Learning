import json
import logging
import RAG.ask 
import RAG.ask_crag
import RAG.memory as memory
import RAG.memory as memory

from logger_config import setup_logging
from RAG.rag_common import open_db, TOP_K, MAX_CONTEXT, chat

setup_logging()

logger = logging.getLogger(__name__)

# ----------------- 1. Naive RAG Runner -----------------
def run_naive_rag(session_name: str, query: str):
    db = open_db()
    mem = memory.open_memory()
    sid = memory.get_session(mem, session_name)
    turns = memory.recent_turns(mem, sid)

    # 1. Rephrasing a follow-up question so that it is self-explanatory
    standalone = memory.rewrite_question(query, turns)
    results = RAG.ask.search(db, standalone, TOP_K)

    # 2. Prompt construction and incorporating previous conversation
    prompt_msgs = RAG.ask.build_prompt(standalone, results)
    messages = memory.add_history_to_prompt(prompt_msgs, turns)
    answer = chat(messages)

    # 3. Preparing the contexts for display in the Expander
    retrieved_contexts = [
        {
            "file": path, 
            "loc": loc,
            "sim": f"{sim:.3f}", 
            "text": text
        }
        for sim, path, loc, text in results
    ]

    # 3. Saving the conversation to the history
    sources = [f"{path} | {loc}" for _, path, loc, _ in results]
    memory.save_turn(mem, sid, query, standalone, answer, sources, "naive")

    return answer, retrieved_contexts

# ----------------- 2. Corrective RAG (CRAG) Runner -----------------
def run_corrective_rag(session_name: str, query: str):
    db = open_db()
    
    # 1. Accessing memory and reading previous rounds for the specified session
    mem = memory.open_memory()
    sid = memory.get_session(mem, session_name)
    turns = memory.recent_turns(mem, sid)

    # 2. Converting a sequential question into an independent, self-contained question
    standalone = memory.rewrite_question(query, turns)
    
    log = RAG.ask_crag.Log()
    
    # 3. Running corrective search and evaluation using the standalone question
    chunks, status, missing = RAG.ask_crag.corrective_retrieve(db, standalone, log)
    
    # If no results are found at all
    if not chunks:
        answer = RAG.ask_crag.NOT_COVERED
        # Save the turn, even if no answer is found, to keep track of the conversation context
        memory.save_turn(mem, sid, query, standalone, answer, [], "crag")
        return answer, [], log

    # 4. Recalculating the similarity based on the original query vector
    for c in chunks:
        if c.get("via") != "question":
            c["sim"] = RAG.ask_crag.similarity_to(db, log.qvec, c["id"])
            
    chunks = sorted(chunks, key=lambda c: -c["sim"])[:MAX_CONTEXT]
    results = [(c["sim"], c["path"], c["loc"], c["text"]) for c in chunks]

    # 5. Constructing the prompt and incorporating conversation history into it
    messages = RAG.ask_crag.build_prompt(standalone, results)
    if status == "PARTIAL":
        gap = f" Likely missing: {missing}." if missing else ""
        messages[1]["content"] += (
            f"\n\nNOTE: the search could not find everything.{gap} "
            "Answer what the sources support and say clearly which parts the documents do not cover."
        )

    # Including previous conversations as background in the prompt message
    memory.add_history_to_prompt(messages, turns)
    
    # Model invocation
    answer = chat(messages)
    
    # 6. Preparing contexts for display in the interface
    retrieved_contexts = [
        {
            "file": c["path"],
            "loc": c["loc"],
            "sim": f"{c['sim']:.3f}",
            "via": c.get("via", "question"),
            "text": c["text"]
        }
        for c in chunks
    ]

    # 7. Save the turn to the in-memory database chat_history.db
    sources = [f"{c['path']} | {c['loc']}" for c in chunks]
    memory.save_turn(mem, sid, query, standalone, answer, sources, "crag")
    
    return answer, retrieved_contexts, log

# ----------------- UI History Load -----------------
def load_db_history(session_name: str, system_name: str):
    """Reading the conversation history for Naive or Corrective from SQLite"""
    try:
        mem = memory.open_memory()
        sid = memory.get_session(mem, session_name, create=False)
        if sid is None:
            return []
        
        # Retrieving conversations specific to this particular system (naive or crag)
        rows = mem.execute(
            "SELECT question, answer, sources FROM turns WHERE session_id = ? AND system = ? ORDER BY id ASC",
            (sid, system_name)
        ).fetchall()
        
        history = []
        for q, a, src in rows:
            sources_list = json.loads(src or "[]")
            history.append({
                "query": q,
                "answer": a,
                "rag_context": "\n".join(sources_list) if sources_list else ""
            })
        return history
    except Exception as e:
        logger.error(f"Error loading DB history: {e}")
        return []
