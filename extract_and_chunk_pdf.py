import os
import re
import tempfile
from pypdf import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def get_valid_pdf_path(pdf_source):
    # If the input is text
    if isinstance(pdf_source, str):
        return pdf_source
    
    # If a Gradio File object
    if hasattr(pdf_source, 'name') and isinstance(pdf_source.name, str) and os.path.exists(pdf_source.name):
        return pdf_source.name
        
    # If the Streamlit UploadedFile object
    if hasattr(pdf_source, 'getbuffer'):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_source.getbuffer())
            return tmp.name

    # Attempting to read bytes if read() exists
    if hasattr(pdf_source, 'read'):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(pdf_source.read())
            return tmp.name
            
    raise ValueError("File type not supported or invalid")

def extract_and_chunk_pdf(pdf_path, chunk_size=1000, chunk_overlap=200):

    # validate the file
    valid_pdf_path = get_valid_pdf_path(pdf_path)

    reader = PdfReader(pdf_path)
    
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
            cleaned_chunk = re.sub(r'\s+', ' ', chunk).strip()
            if len(cleaned_chunk) > 30:
                chunks.append(cleaned_chunk)
                metadatas.append({"page": page_idx, "source": pdf_path})
                
    print(f" {len(chunks)} Chunks was created successfully with page numbers. ")
    return chunks, metadatas