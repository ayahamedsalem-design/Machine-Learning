import os
import re
import uuid
import logging
import tempfile
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter

try:
    from RAGs.logger_config import setup_logging
except ModuleNotFoundError:
    from logger_config import setup_logging

# ==========================================
# 1. Utility Functions (Setup & File Handling)
# ==========================================

setup_logging()

logger = logging.getLogger(__name__)

# prompts.py

SYS_PROMPT = """You are an expert analytical research assistant managing a vast knowledge base.
Answer all aspects of the user's question(s) thoroughly and accurately based on BOTH the provided context below AND the conversation history.
- Use the conversation history to understand follow-up questions, pronouns, or previously discussed topics.
- If the question requires new facts, rely on the [Context from Global Database].
- If multiple questions are asked, address each question in a separate, clearly structured section.
- **IMPORTANT**: Cite the Source File and Page number mentioned in the context headers when stating facts.
- If an answer or detail cannot be found in the context or the conversation history, explicitly state: 'The answer does not exist in the available database'."""

# Initialization and Environment Setup
def initialize_api():
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    return OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=30)


def resolve_file_name(pdf_source) -> str:
    """Safely extracts the base filename from either a file path string or an UploadedFile object."""
    if hasattr(pdf_source, "name") and isinstance(pdf_source.name, str):
        return os.path.basename(pdf_source.name)
    return os.path.basename(str(pdf_source))


def get_valid_pdf_path(pdf_source):
    """Ensures a valid readable local file path for the PDF."""
    if isinstance(pdf_source, str):
        return pdf_source
     
     # If a Gradio File object   
    if hasattr(pdf_source, "name") and isinstance(pdf_source.name, str) and os.path.exists(pdf_source.name):
        return pdf_source.name
        
     # If the Streamlit UploadedFile object
    if hasattr(pdf_source, "getbuffer"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_source.getbuffer())
            return tmp.name
     # Attempting to read bytes if read() exists       
    if hasattr(pdf_source, "read"):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_source.read())
            return tmp.name
    raise ValueError("File type not supported or invalid")


def get_full_text(pdf_path):
    """Extracts and concatenates text from all pages of the PDF."""
    valid_pdf_path = get_valid_pdf_path(pdf_path)
    reader = PdfReader(valid_pdf_path)
    return "".join([page.extract_text() or "" for page in reader.pages])

def decompose_multi_questions(user_query: str) -> list:
    """Decomposes compound queries into individual sub-questions."""
    parts = re.split(r"[\n?؟;]+", user_query)
    sub_queries = [p.strip() for p in parts if len(p.strip()) > 5]
    if not sub_queries:
        sub_queries = [user_query.strip()]
    logger.info(f"Query decomposed into {len(sub_queries)} sub-questions: {sub_queries}")
    return sub_queries

# ==========================================
# 2. Chunking Function 1: Standard (For Basic & Hybrid)
# ==========================================

def extract_and_chunk_standard(pdf_path, chunk_size=1000, chunk_overlap=200):
    """
    Standard recursive chunking with page number and source filename metadata.
    Used by: Basic RAG, Hybrid RAG
    """
    valid_pdf_path = get_valid_pdf_path(pdf_path)
    file_name = resolve_file_name(pdf_path)
    reader = PdfReader(valid_pdf_path)

    # 1. Set up the Splitter for smart cutting that preserves paragraphs and sentences.
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )

    chunks = []
    metadatas = []

    # 2. Extract the text page by page and save the page number in the metadata
    for page_idx, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()
        if not page_text:
            continue

        page_chunks = text_splitter.split_text(page_text)
        for chunk in page_chunks:
            # Clean up extra spaces
            cleaned_chunk = re.sub(r"\s+", " ", chunk).strip()
            if len(cleaned_chunk) > 30:
                chunks.append(cleaned_chunk)
                metadatas.append({"page": page_idx, "source": file_name})

    logger.info(f"[Standard Chunking] Created successfully {len(chunks)} chunks for {file_name}.")
    return chunks, metadatas


# ==========================================
# 3. Chunking Function 2: Hierarchical (For Parent-Child & Parent Corrective RAG)
# ==========================================

def extract_and_chunk_hierarchical(pdf_path, parent_chunk_words=300, child_chunk_words=70, child_overlap=15):
    """
    Hierarchical chunking splitting text into large parent blocks and smaller overlapping child chunks.
    Used by: Parent-Child RAG, Corrective Parent-Child RAG
    """
    file_name = resolve_file_name(pdf_path)
    full_text = get_full_text(pdf_path)
    words = full_text.split()

    parent_ids = []
    parent_texts = []
    child_ids = []
    child_chunks = []
    child_metadatas = []

    for p_idx in range(0, len(words), parent_chunk_words):
        parent_id = f"parent_{uuid.uuid4().hex[:8]}"
        parent_text = " ".join(words[p_idx : p_idx + parent_chunk_words])
        parent_texts.append(parent_text)
        parent_ids.append(parent_id)

        parent_words = parent_text.split()
        step = child_chunk_words - child_overlap
        for c_idx in range(0, len(parent_words), step):
            child_text = " ".join(parent_words[c_idx : c_idx + child_chunk_words])
            if len(child_text.strip()) > 20:
                child_chunks.append(child_text)
                child_ids.append(f"child_{uuid.uuid4().hex[:8]}")
                child_metadatas.append({"parent_id": parent_id, "source": file_name})

    print(f"[Hierarchical Chunking] Created {len(parent_texts)} Parents and {len(child_chunks)} Children for {file_name}.")
    return parent_texts, parent_ids, child_chunks, child_metadatas, child_ids