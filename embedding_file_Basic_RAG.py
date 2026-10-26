
import os
import chromadb
import ollama
from openai import OpenAI
from pypdf import PdfReader
from dotenv import load_dotenv

# Embedding
# 1.1 Get API KEY
load_dotenv()
api_key=os.getenv("Embedded_Model_Key")
client_ai = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key)

def run_basic_RAG(pdf_source, user_query):

    # 1.2 Extract Text From pdf
    reader = PdfReader(pdf_source)
    full_text = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            full_text += text + "\n"
        

    # 1.3 Split To Chunks
    chunk_size = 1000
    chunks = [
        full_text[i : i + chunk_size] for i in range(0, len(full_text), chunk_size - 100)
    ]

    print(f"The Script Splitted to {len(chunks)} chunck.")

    # 1.4 Embeddings with Nvidia Nemotron
    embeddings_list = []
    print("Creating Embeddings via OpenRouter...")

    # Send To API Model
    response = client_ai.embeddings.create(
        model="nvidia/nemotron-3.5-embed-1b:free", input=chunks
    )

    # Append Vectors
    for item in response.data:
        embeddings_list.append(item.embedding)

    # 1.5 Store In ChromaDB
    chroma_client = chromadb.Client()

    # Delete If Next Run
    try:
        chroma_client.delete_collection(name="pdf_embeddings")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(name="pdf_embeddings")
    
    collection.add(
        documents=chunks,
        embeddings=embeddings_list,
        ids=[f"id_{i}" for i in range(len(chunks))],
    )

    print("Embeddings Saved in ChromaDB Successfully!")

    # 1.6 Get Embeddings Result
    results = collection.get(
        limit=3,
        include=["documents", "metadatas", "embeddings"]
    )

    for i in range(len(results["ids"])):
        print(f"=== [ID: {results['ids'][i]}] ===")
        print(f"Text:\n{results['documents'][i]}...")  
        print(f"Embedding Vector: {len(results['embeddings'][i])} ")
        print(f"Samples: {results['embeddings'][i][:3]}")
        print("-" * 50)

    # Query
    # 2.1 Define The Query
    print(f"Query: {user_query}\n")

    # 2.2 Generate Embedding Vector For The Query
    print("Embedding the query and searching database...")
    query_embedding_res = client_ai.embeddings.create(
        model="nvidia/nemotron-3.5-embed-1b:free",
        input=user_query
    )
    query_vector = query_embedding_res.data[0].embedding

    # 2.3 Retrieve Top Matching Chunks
    results = collection.query(
        query_embeddings=[query_vector],
        n_results=3
    )
    retrieved_chunks = results["documents"][0]
    context_text = "\n\n---\n\n".join(retrieved_chunks)
    print("context text:" + context_text)

    # 2.4 Generate The Answer Using An LLM Based On The Paper
    print("Generating response from context...\n")

    prompt = f"""You are a helpful assistant. Answer the user's question accurately based ONLY on the following context retrieved from the paper:

    [Context]:
    {context_text}

    [Question]:
    {user_query}
    """

    # Using Local Ollama Model
    response = ollama.chat(
            model="llama3.2:1b",
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": 0.0,      # 0.0 makes the output strictly deterministic
                "top_p": 0.1,
                "num_ctx": 4096
            }
        )

    # 2.5 Print The Results
    print("=" * 60)
    print("Model Response:")
    print("=" * 60)
    print(response["message"]["content"])

    return response["message"]["content"], retrieved_chunks


if __name__ == "__main__":
    sample_pdf = r"D:\GitProjects\Machine-Learning\imagenet-classification-with-deep-convolutional-neural-networks-Paper.pdf"
    sample_query = "What is the main architecture of Neural Network and how many layers does it have?"
    
    run_basic_RAG(sample_pdf, sample_query)