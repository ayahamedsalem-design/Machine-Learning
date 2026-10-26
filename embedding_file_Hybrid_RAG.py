import os
import chromadb
import streamlit as st
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi

# Embedding
# 1.1 Get API KEY
load_dotenv()
api_key = os.getenv("Embedded_Model_Key")

client_ai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key
)

def run_hybrid_RAG(pdf_source, user_query):

    # 1.2 Extract text from pdf
    reader = PdfReader(pdf_source)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"

    # 1.3 Chunking
    chunk_size = 800
    overlap = 100
    chunks = []

    step = chunk_size - overlap
    for i in range(0, len(full_text), step):
        segment = full_text[i:i + chunk_size].strip()
        if len(segment) > 30:
            chunks.append(segment)

    print(f"Total Chunks created: {len(chunks)}")

    # 1.4 Prepare BM25 Keyword Search Index (Sparse Index)
    tokenized_corpus = [chunk.lower().split() for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    print("BM25 index built successfully.")

    # 1.5 Prepare Vector Database (Dense Index)
    chroma_client = chromadb.PersistentClient(path="./chroma_db_hybrid")

    # Delete If Next Run
    try:
        chroma_client.delete_collection(name="pdf_embeddings")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(name="hybrid_chunks")

    # Check if collection is already populated to save API calls
    if collection.count() == 0:
        print("Generating embeddings for vector index...")
        batch_size = 15
        embeddings_list = []
        
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]

            response = client_ai.embeddings.create(
                model="nvidia/nemotron-3.5-embed-1b:free",
                input=batch
            )

            for item in response.data:
                embeddings_list.append(item.embedding)

        chunk_ids = [f"doc_{i}" for i in range(len(chunks))]

        collection.add(
            documents=chunks,
            embeddings=embeddings_list,
            ids=chunk_ids
        )
        print("Vector database populated successfully.")
    else:
        print(f"Loaded existing {collection.count()} vectors from ChromaDB.")

    # 2.1 Define Query
    print(f"\nUser Query: {user_query}\n")

    # STEP A: Dense / Vector Search 
    print("Running Dense / Vector Search...")

    query_vec_res = client_ai.embeddings.create(
        model="nvidia/nemotron-3.5-embed-1b:free",
        input=user_query
    )
    query_vec = query_vec_res.data[0].embedding

    vector_results = collection.query(
        query_embeddings=[query_vec],
        n_results=5
    )
    dense_retrieved_chunks = vector_results["documents"][0]

    # STEP B: Sparse / BM25 Keyword Search 
    print("Running Sparse / BM25 Keyword Search...")

    tokenized_query = user_query.lower().split()
    bm25_top_chunks = bm25.get_top_n(tokenized_query, chunks, n=5)

    # STEP C: Reciprocal Rank Fusion (RRF) 
    # Combine scores from both retrievers to pick the ultimate top results
    rrf_k = 60
    scores = {}

    # Score Dense results
    for rank, doc in enumerate(dense_retrieved_chunks):
        scores[doc] = scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Score Sparse results
    for rank, doc in enumerate(bm25_top_chunks):
        scores[doc] = scores.get(doc, 0.0) + (1.0 / (rrf_k + rank + 1))

    # Sort documents by combined RRF score
    ranked_docs = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    top_hybrid_chunks = [doc for doc, score in ranked_docs[:3]]

    combined_context = "\n\n---\n\n".join(top_hybrid_chunks)

    # 2.2 Generate The Answer Using An LLM Based On The Paper
    print("Generating final response from hybrid context...\n")

    prompt = f"""You are a helpful assistant. Answer the user's question accurately based ONLY on the following context retrieved from the paper:

    [Context]:
    {combined_context}

    [Question]:
    {user_query}

    """

    completion = client_ai.chat.completions.create(
        model="openrouter/auto",  # Automatically selects available free route or specify your active model
        messages=[{"role": "user", "content": prompt}]
    )

    # 2.3 Print The Results
    print("\n" + "=" * 60)
    print("Top Hybrid Retrieved Chunks (Dense + Sparse):")
    print("=" * 60)
    for i, chunk in enumerate(top_hybrid_chunks):
        print(f"\n[Hybrid Chunk {i+1}]:")
        print(chunk.strip())

    print("=" * 60)
    print("Hybrid RAG Response:")
    print("=" * 60)
    print(completion.choices[0].message.content)

    return completion.choices[0].message.content, top_hybrid_chunks


if __name__ == "__main__":
    sample_pdf = r"D:\GitProjects\Machine-Learning\Precision Medicine.pdf"
    sample_query = "What specific clinical benefits does precision medicine provide for rare diseases and cancer therapies?"
    
    run_hybrid_RAG(sample_pdf, sample_query)