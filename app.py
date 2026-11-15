import os
import logging
import streamlit as st
from dotenv import load_dotenv

# Global RAG imports from RAGs package
from RAGs.logger_config import setup_logging
from RAGs.basic_RAG import run_basic_RAG, index_basic_rag
from RAGs.parent_child_RAG import (
    run_parent_child_chunking_RAG,
    index_parent_child_rag,
)
from RAGs.hybrid_RAG import run_hybrid_chat_session, initialize_hybrid_index
from RAGs.corrective_parent_child_RAG import run_corrective_parent_child_rag
from RAGs.corrective_hybrid_RAG import run_corrective_hybrid_rag
from RAGs.history_summarizer import summarize_cross_file_history
from RAGs.RAG_service import execute_with_retry
from RAGs.chat_history import load_file_history, clear_all_history, load_all_history

# Legacy RAG imports from RAG package
from RAG.app_bridge import run_naive_rag, run_corrective_rag, load_db_history

# Initializes logging (writes logging_config.json on first run)
setup_logging()
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

st.set_page_config(page_title="Global Knowledge Base RAG", page_icon="🤖", layout="wide")
st.title("Enterprise Global RAG System ")
st.markdown(
    "Query across **ALL** your indexed documents using Global architectures or External RAG pipelines."
)
st.divider()

# Unified session ID for global cross-document chat history
GLOBAL_SESSION_ID = "global_chat_session"

# ==========================================
# 1. Sidebar: Knowledge Base Ingestion & Settings
# ==========================================
with st.sidebar:
    st.header("1. Feed the Knowledge Base")
    st.info("Upload PDF documents here to index them permanently into the Global Database.")

    uploaded_file = st.file_uploader("Upload PDF to Global DB:", type=["pdf"], key="global_uploader")

    if uploaded_file:
        if st.button("Index File into Global DB", use_container_width=True):
            with st.spinner(f"Indexing '{uploaded_file.name}' across Basic, Hierarchical, and Hybrid DBs..."):
                try:
                    # Index into all Global RAG architectures simultaneously
                    index_basic_rag(uploaded_file)
                    index_parent_child_rag(uploaded_file)
                    initialize_hybrid_index(uploaded_file)

                    logger.info(f"Successfully indexed '{uploaded_file.name}' into all Global DBs.")
                    st.success(f"'{uploaded_file.name}' added to the Global Database!")
                except Exception as e:
                    logger.error(f"Indexing failed for '{uploaded_file.name}': {e}", exc_info=True)
                    st.error(f"Error during indexing: {e}")

    st.divider()
    st.header("2. Query Architecture")
    rag_type = st.radio(
        "Choose RAG Architecture:",
        (
            "Basic RAG",
            "Parent-Child (Hierarchical) RAG",
            "Hybrid RAG",
            "Corrective Parent-Child RAG",
            "Corrective Hybrid RAG",
            "Ext Naive RAG",
            "Ext Corrective RAG"
         ),
        index=0,
    )

    st.markdown("---")
    if st.button("Clear Chat History", use_container_width=True):
        clear_all_history()
        logger.info("Global chat history cleared.")
        st.success("All history cleared!")
        st.rerun()

    if st.button("Summarize History", use_container_width=True):
        all_history = load_all_history()
        if not all_history:
            st.warning("No history available to summarize.")
        else:
            with st.spinner("Summarizing conversation history..."):
                history_text = "\n".join(
                    [f"Q: {item.get('query')} | A: {item.get('answer')}" for item in all_history]
                )
                try:
                    summary = summarize_cross_file_history(history_text)
                    st.markdown("**📝 Global History Summary**")
                    st.info(summary)
                except Exception as e:
                    logger.error(f"Summary generation failed: {e}", exc_info=True)
                    st.error(f"Failed to generate summary: {e}")


# ==========================================
# 2. Main Area: Chat Interface
# ==========================================
# Identify if the selected architecture is an external one
is_ext_mode = "Ext" in rag_type

# Load appropriate conversation history based on Global vs Ext mode
if is_ext_mode:
    system_key = "naive" if "Naive" in rag_type else "crag"
    # Assuming GLOBAL_SESSION_ID is used as the session name for external RAGs as well
    active_history = load_db_history(GLOBAL_SESSION_ID, system_name=system_key)
else:
    active_history = load_file_history(GLOBAL_SESSION_ID)

# Render chat history
for message in active_history:
    with st.chat_message("user"):
        st.markdown(message["query"])
    with st.chat_message("assistant"):
        st.markdown(message["answer"])
        if "rag_context" in message and message["rag_context"]:
            with st.expander("View Retrieved Context Chunks"):
                st.text(message["rag_context"])

# Handle new user input
user_query = st.chat_input("Ask any question...")

if user_query:
    logger.info(f"Processing query via {rag_type}")
    with st.chat_message("user"):
        st.markdown(user_query)

    with st.chat_message("assistant"):
        with st.spinner(f"Running {rag_type}..."):
            try:
                # Route to Global Multi-Document Architectures
                if rag_type == "Basic RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_basic_RAG, user_query
                    )
                elif rag_type == "Parent-Child (Hierarchical) RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_parent_child_chunking_RAG, user_query
                    )
                elif rag_type == "Hybrid RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_hybrid_chat_session, user_query
                    )
                elif rag_type == "Corrective Parent-Child RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_corrective_parent_child_rag, user_query
                    )
                elif rag_type == "Corrective Hybrid RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_corrective_hybrid_rag, user_query
                    )

                # Route to External Architectures (Session Name + Query)
                elif rag_type == "Ext Naive RAG":
                    answer, retrieved_contexts = execute_with_retry(
                        run_naive_rag, GLOBAL_SESSION_ID, user_query
                    )
                elif rag_type == "Ext Corrective RAG":
                    result = execute_with_retry(
                        run_corrective_rag, GLOBAL_SESSION_ID, user_query
                    )
                    if len(result) == 3:
                        answer, retrieved_contexts, crag_log = result
                    else:
                        answer, retrieved_contexts = result

                st.subheader("Model Response")
                st.write(answer)

                with st.expander("View Retrieved Context Chunks"):
                    if isinstance(retrieved_contexts, list):
                        for idx, chunk in enumerate(retrieved_contexts):
                            st.markdown(f"**Chunk [{idx + 1}]**")
                            if isinstance(chunk, dict):
                                text_content = (
                                    chunk.get("text")
                                    or chunk.get("page_content")
                                    or str(chunk)
                                )
                            else:
                                text_content = str(chunk)
                            st.text(text_content.strip())
                            st.markdown("---")
                    else:
                        st.text(str(retrieved_contexts))

            except Exception as e:
                logger.critical(f"Fatal error during {rag_type} execution: {e}", exc_info=True)
                st.error(f"An error occurred during execution: {e}")