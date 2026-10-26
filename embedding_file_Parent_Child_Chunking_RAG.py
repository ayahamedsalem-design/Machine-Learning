import os
import math
import uuid
import chromadb
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

# Embedding
# 1.1 Get API KEY
load_dotenv()
api_key = os.getenv("Embedded_Model_Key")

client_ai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

def run_parent_child_chunking_RAG(pdf_source, user_query):

    # 1.2 Extract text from pdf
    reader = PdfReader(pdf_source)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    # 1.3 Parent-Child Chunking 
    parent_chunk_size = 1800
    child_chunk_size = 400
    child_overlap = 50

    parent_docs = {}
    child_chunks = []
    child_metadatas = []
    child_ids = []

    # Generate Parent Chunks
    for p_idx in range(0, len(full_text), parent_chunk_size):
        parent_id = f"parent_{uuid.uuid4().hex[:8]}"
        parent_text = full_text[p_idx:p_idx + parent_chunk_size]
        parent_docs[parent_id] = parent_text

        # Generate Child Chunks from this Parent
        step = child_chunk_size - child_overlap
        for c_idx in range(0, len(parent_text), step):
            child_text = parent_text[c_idx:c_idx + child_chunk_size]
            if len(child_text.strip()) > 20:  # Skip empty or very short snippets
                child_chunks.append(child_text)
                child_metadatas.append({"parent_id": parent_id})
                child_ids.append(f"child_{uuid.uuid4().hex[:8]}")

    print(f"Total Parent Chunks: {len(parent_docs)}")
    print(f"Total Child Chunks created: {len(child_chunks)}")

    # 1.4 Generate Embeddings for Child Chunks 
    batch_size = math.ceil(len(child_chunks) / 15) # limit the model calls to 15 to get around the free-tier limitation (20 call/min)
    print(batch_size)
    child_embeddings = []

    print("Generating embeddings for child chunks...")

    for i in range(0, len(child_chunks), batch_size):
        batch = child_chunks[i:i + batch_size]

        response = client_ai.embeddings.create(
            model="nvidia/nemotron-3.5-embed-1b:free",
            input=batch
        )

        for item in response.data:
            child_embeddings.append(item.embedding)

    # 1.5 Store Child Chunks in ChromaDB
    chroma_client = chromadb.PersistentClient(path="./chroma_db_hierarchical")

    # Delete If Next Run
    try:
        chroma_client.delete_collection(name="pdf_embeddings")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(name="child_embeddings")

    collection.add(
        documents=child_chunks,
        embeddings=child_embeddings,
        metadatas=child_metadatas,
        ids=child_ids
    )
    print("All child embeddings saved to ChromaDB successfully.")

    # Query
    # 2.1 Query and Retrieve using Parent Context
    print(f"\nUser Query: {user_query}")

    query_resp = client_ai.embeddings.create(
        model="nvidia/nemotron-3.5-embed-1b:free",
        input=user_query
    )
    query_vec = query_resp.data[0].embedding

    # 2.2 Search top 4 matching child chunks
    search_results = collection.query(
        query_embeddings=[query_vec],
        n_results=4
    )

    # 2.3 Retrieve distinct Parent Chunks from matched children
    matched_parent_ids = set()
    for meta in search_results["metadatas"][0]:
        matched_parent_ids.add(meta["parent_id"])

    retrieved_parents = [parent_docs[pid] for pid in matched_parent_ids if pid in parent_docs]
    full_context = "\n\n---\n\n".join(retrieved_parents)

    # 2.4 Generate The Answer Using An LLM Based On The Paper
    print("Generating LLM response with parent context...\n")
    prompt = f"""You are a helpful assistant. Answer the user's question accurately based ONLY on the following context retrieved from the paper:

    [Context]:
    {full_context}

    [Question]:
    {user_query}

    """

    completion = client_ai.chat.completions.create(
        model="nvidia/nemotron-3.5-super-vl:free",
        messages=[{"role": "user", "content": prompt}]
    )

    # 2.5 Print The Results
    print("=" * 60)
    print("Model Response:")
    print("=" * 60)
    print(completion.choices[0].message.content)

    return completion.choices[0].message.content, retrieved_parents


if __name__ == "__main__":
    sample_pdf = r"D:\GitProjects\Machine-Learning\Advice For Risk Associated with Cultured Meat.pdf"
    sample_query = "What are the main chemical and microbiological hazards identified during the different stages of cultured meat production, and why is there significant uncertainty regarding the health risks for tasting participants?"

    run_parent_child_chunking_RAG(sample_pdf, sample_query)