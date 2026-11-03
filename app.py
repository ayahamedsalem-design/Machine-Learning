import logging
from logger_config import setup_logging
import streamlit as st
from dotenv import load_dotenv
from chat_history import load_file_history, clear_all_history, load_all_history

# Import the modular RAG functions from your local files
from embedding_file_Basic_RAG import run_basic_RAG
from embedding_file_Parent_Child_Chunking_RAG import run_parent_child_chunking_RAG
from embedding_file_Hybrid_RAG import run_hybrid_chat_session
from history_summarizer import summarize_cross_file_history
from RAG.app_bridge import run_naive_rag, run_corrective_rag, load_db_history
from RAG_service import execute_with_retry

# Initializes logging (writes logging_config.json on first run)
setup_logging()

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Streamlit Page Setup
st.set_page_config(page_title="Universal RAG System", page_icon="🤖", layout="wide")

logger.debug(
    "Streamlit script execution triggered. Initializing environment variables and state."
)
logger.info("Starting the UI")

st.title("Multi-Architecture RAG System")
st.markdown(
    "Query your PDF documents using **Basic**, **Hierarchical (Parent-Child)**, **Hybrid**, **Naive**, or **Corrective** RAG retrieval methods."
)

st.divider()

if "current_file" not in st.session_state:
    st.session_state.current_file = None
    logger.debug("Session state 'current_file' initialized to None.")

# Left Sidebar: Architecture Selection
with st.sidebar:
    st.header("RAG Systems")

    rag_type = st.radio(
        "Choose RAG Architecture:",
        ("Basic RAG", "Hierarchical (Parent-Child) RAG", "Hybrid RAG", "Naive RAG", "Corrective RAG"),
        index=2,
    )

    st.markdown("---")
    st.markdown("**Architecture Details:**")
    if rag_type == "Basic RAG":
        st.info("Standard vector similarity search with fixed-size chunks.")
    elif rag_type == "Hierarchical (Parent-Child) RAG":
        st.info(
            "Embeds small child chunks for precise retrieval and returns full parent context."
        )
    elif rag_type == "Hybrid RAG":
        st.info(
            "Combines dense semantic vector retrieval with sparse BM25 keyword matching via RRF."
        )

    elif rag_type == "Naive RAG":
        st.info(
                    "Standard top-k vector similarity search without grading."
                )
    else:
        st.info(
                    "Retrieves candidates, grades relevance via LLM, and refetches missing parts if needed."
                )
        
    st.markdown("---")
    # A button to clear the conversation and start over
    if st.button("Clear Chat History", use_container_width=True):
        clear_all_history()
        logger.info("Chat history cleared")
        st.success("All cross-file history cleared!")
        st.rerun()

    # Placeholder for summarization
    if st.button("Summarize History", use_container_width=True):
        logger.info("Summarization process triggered using Hybrid RAG model")
        all_history = load_all_history()

        if not all_history:
            logger.warning(
                "Summarization requested, but no cross-file history was found."
            )
            st.warning("No history available to summarize.")
        else:
            with st.spinner("Summarizing across all files using Nemotron..."):
                # Concatenate all Q&A across the multiple documents
                history_text = "\n".join(
                    [
                        f"File: {item.get('file_name', 'Unknown')} | Q: {item.get('query')} | A: {item.get('answer')}"
                        for item in all_history
                    ]
                )

                try:
                    summary = summarize_cross_file_history(history_text)
                    logger.info("History summarization completed successfully.")
                    st.markdown("**📝 Global History Summary**")
                    st.info(summary)
                except Exception as e:
                    logger.error(
                        f"Failed to generate history summary: {e}", exc_info=True
                    )
                    st.error(f"Failed to generate summary: {e}")

# File Upload & Query Form
uploaded_file = st.file_uploader("Upload your PDF:", type=["pdf"])

# Reset History if a different file was uploaded
if uploaded_file and uploaded_file.name != st.session_state.current_file:
    logger.debug(f"New file uploaded: {uploaded_file.name}. Updating session state.")
    st.session_state.current_file = uploaded_file.name

# View previous conversations loaded directly from JSON
if uploaded_file:
    if rag_type == "Naive RAG":
          file_history = load_db_history(uploaded_file.name, system_name="naive")
    elif rag_type == "Corrective RAG":
          file_history = load_db_history(uploaded_file.name, system_name="crag")
    else: file_history = load_file_history(uploaded_file.name)
    for message in file_history:
        with st.chat_message("user"):
            st.markdown(message["query"])
        with st.chat_message("assistant"):
            st.markdown(message["answer"])
            if "rag_context" in message and message["rag_context"]:
                with st.expander("View Retrieved Context Chunks"):
                    st.text(message["rag_context"])

# Receive new questions via chat_input
user_query = st.chat_input("Ask a question about the document...")

if user_query:
    if not uploaded_file:
        logger.warning("User submitted a query without uploading a PDF document first.")
        st.warning("Please upload a PDF file first.")
    else:
        logger.info(f"Processing user query via {rag_type}")
        with st.chat_message("user"):
            st.markdown(user_query)

        # Processing & Output
        with st.chat_message("assistant"):
            with st.spinner(f"Running {rag_type}..."):
                try:
                    # run the chosen RAG
                    if rag_type == "Basic RAG":
                        answer, retrieved_contexts = execute_with_retry(
                            run_basic_RAG,
                            uploaded_file, 
                            user_query
                        )
                    elif rag_type == "Hierarchical (Parent-Child) RAG":
                        answer, retrieved_contexts =execute_with_retry(
                            run_parent_child_chunking_RAG,
                            uploaded_file, 
                            user_query
                        )
                    elif rag_type == "Hybrid RAG":
                        answer, retrieved_contexts = execute_with_retry(
                            run_hybrid_chat_session,
                            uploaded_file, 
                            user_query
                        )
                    elif rag_type == "Naive RAG":
                        answer, retrieved_contexts = execute_with_retry(
                            run_naive_rag,
                            uploaded_file.name,
                            user_query
                        )
                    else:
                        result = execute_with_retry(
                            run_corrective_rag,
                            uploaded_file.name,
                            user_query
                        )
                        if len(result) == 3:
                           answer, retrieved_contexts, crag_log = result
                        else:
                           answer, retrieved_contexts = result
                           logger.info("RAG execution completed successfully.")
                           st.success("Execution completed successfully!")

                    # Display the Model Response
                    st.subheader("Model Response")
                    st.write(answer)

                    # Collapsible view for the retrieved context chunks
                    with st.expander("View Retrieved Context Chunks"):
                        if isinstance(retrieved_contexts, list):
                            for idx, chunk in enumerate(retrieved_contexts):
                                st.markdown(f"**Chunk [{idx + 1}]**")

                                # Extracting text, whether it's dict or str
                                if isinstance(chunk, dict):
                                    # If it is a dictionary, we look for the key that contains the text
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
                    logger.critical(
                        f"Fatal error during {rag_type} execution: {e}", exc_info=True
                    )
                    st.error(f"An error occurred during execution: {e}")
