import streamlit as st
from dotenv import load_dotenv

# Import the modular RAG functions from your local files
from embedding_file_Basic_RAG import run_basic_RAG
from embedding_file_Parent_Child_Chunking_RAG import run_parent_child_chunking_RAG
from embedding_file_Hybrid_RAG import run_hybrid_RAG

# Load environment variables
load_dotenv()

# Streamlit Page Setup
st.set_page_config(
    page_title="Universal RAG System",
    page_icon="🤖",
    layout="wide"
)

st.title("Multi-Architecture RAG System")
st.markdown("Query your PDF documents using **Basic**, **Hierarchical (Parent-Child)**, or **Hybrid** RAG retrieval methods.")

st.divider()

# Left Sidebar: Architecture Selection
with st.sidebar:
    st.header("RAG Systems")
    
    rag_type = st.radio(
        "Choose RAG Architecture:",
        (
            "Basic RAG",
            "Hierarchical (Parent-Child) RAG",
            "Hybrid RAG"
        ),
        index=0
    )
    
    st.markdown("---")
    st.markdown("**Architecture Details:**")
    if rag_type == "Basic RAG":
        st.info("Standard vector similarity search with fixed-size chunks.")
    elif rag_type == "Hierarchical (Parent-Child) RAG":
        st.info("Embeds small child chunks for precise retrieval and returns full parent context.")
    else:
        st.info("Combines dense semantic vector retrieval with sparse BM25 keyword matching via RRF.")

# File Upload & Query Form
uploaded_file = st.file_uploader("Upload your PDF:", type=["pdf"])

user_query = st.text_area(
    "Enter your query:",
    placeholder="e.g., What are the main concepts discussed in the document?",
    height=100
)

run_button = st.button("Run RAG Query", use_container_width=True)

# Processing & Output
if run_button:
    if not uploaded_file:
        st.warning("Please upload a PDF file first.")
    elif not user_query.strip():
        st.warning("Please enter a question to ask.")
    else:
        with st.spinner(f"Running {rag_type}..."):
            try:
                # run the chosen RAG
                if rag_type == "Basic RAG":
                    answer, retrieved_contexts = run_basic_RAG(uploaded_file, user_query)
                elif rag_type == "Hierarchical (Parent-Child) RAG":
                    answer, retrieved_contexts = run_parent_child_chunking_RAG(uploaded_file, user_query)
                else:
                    answer, retrieved_contexts = run_hybrid_RAG(uploaded_file, user_query)

                st.success("Execution completed successfully!")

                # Display the Model Response
                st.subheader("Model Response")
                st.write(answer)

                # Collapsible view for the retrieved context chunks
                with st.expander("View Retrieved Context Chunks"):
                    if isinstance(retrieved_contexts, list):
                        for idx, chunk in enumerate(retrieved_contexts):
                            st.markdown(f"**Chunk [{idx + 1}]**")
                            st.text(chunk.strip())
                            st.markdown("---")
                    else:
                        st.text(str(retrieved_contexts))

            except Exception as e:
                st.error(f"An error occurred during execution: {e}")
