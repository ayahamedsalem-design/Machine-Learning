import os
import re
import chromadb
from openai import OpenAI
from dotenv import load_dotenv
from rank_bm25 import BM25Okapi
from chat_history import persist_chat_history
from extract_and_chunk_pdf import get_valid_pdf_path
from extract_and_chunk_pdf import extract_and_chunk_pdf
from chat_history import persist_chat_history, load_file_history

# Embedding
# 1.1 Initialization and Environment Setup
load_dotenv()
api_key = os.getenv("OPENROUTER_API_KEY")

client_ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=30)


# 1.2 Extract text from pdf
# A dedicated function for cleaning and cutting words for BM25 to remove punctuation marks.
def bm25_tokenizer(text):
    return re.findall(r"\b\w+\b", text.lower())



def initialize_hybrid_index(pdf_source):

    # 1.2 Text extraction and smart segmentation with page numbers
    chunks, metadatas = extract_and_chunk_pdf(
        pdf_source, chunk_size=1000, chunk_overlap=200
    )

    # Convert chunks to raw text in case they are Document objects
    clean_chunks = [
        c.page_content if hasattr(c, "page_content") else str(c) for c in chunks
    ]

    if not clean_chunks:
        raise ValueError("Error: No chunks extracted from the PDF file.")

    # 1.3 Prepare a BM25 index with enhanced keyword processing
    tokenized_corpus = [bm25_tokenizer(chunk) for chunk in chunks]
    bm25 = BM25Okapi(tokenized_corpus)
    print("BM25 index built successfully.")

    # 1.5 Prepare Vector Database (Dense Index)
    chroma_client = chromadb.PersistentClient(path="./chroma_db_hybrid")

    # Use a collection name linked to the filename to avoid document overlap
    file_name = getattr(pdf_source, "name", str(pdf_source))
    pdf_base_name = os.path.splitext(os.path.basename(file_name))[0]

    # Clean the name to correspond with ChromaDB name requirements (letters and numbers only)
    safe_collection_name = re.sub(r"[^a-zA-Z0-9_-]", "_", pdf_base_name)[:50]

    # Delete If Next Run
    try:
        chroma_client.delete_collection(name="pdf_embeddings")
    except Exception:
        pass

    collection = chroma_client.get_or_create_collection(name=safe_collection_name)

    # Check if collection is already populated to save API calls
    if collection.count() == 0:
        print("Generating embeddings for vector index...")
        batch_size = 15
        embeddings_list = []

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]

            response = client_ai.embeddings.create(
                model="nvidia/nemotron-3.5-embed-1b:free", input=batch
            )

            for item in response.data:
                embeddings_list.append(item.embedding)

        chunk_ids = [f"doc_{i}" for i in range(len(clean_chunks))]

        collection.add(
            documents=clean_chunks,
            embeddings=embeddings_list,
            metadatas=metadatas,  # store page numbers
            ids=chunk_ids,
        )
        print("Vector database populated successfully.")
    else:
        print(f"Loaded existing {collection.count()} vectors from ChromaDB.")

    return bm25, collection, chunks, metadatas


def retrieve_hybrid_context(user_query, bm25, collection, chunks, metadatas, top_k=5):

    # Ensure retrieval count does not exceed total available chunks
    t_chunks_limit = min(10, len(chunks))

    # 2.1 Define Query
    print(f"\nUser Query: {user_query}\n")

    # STEP A: Dense (Vector) Sementaic Search
    print("Running Dense (Vector) Sementaic Search...")

    # Dense (Vector) Retrieval
    query_vec_res = client_ai.embeddings.create(
        model="nvidia/nemotron-3.5-embed-1b:free", input=user_query
    )
    query_vec = query_vec_res.data[0].embedding

    vector_results = collection.query(
        query_embeddings=[query_vec],
        n_results=t_chunks_limit,  # increase return chuncks to 10
    )
    dense_retrieved_chunks = (
        vector_results["documents"][0] if vector_results["documents"] else []
    )

    # STEP B: Sparse (BM25) Keyword Search
    print("Running Sparse (BM25) Keyword Search...")

    # Sparse (BM25) Keyword Retrieval
    tokenized_query = bm25_tokenizer(user_query)

    # retrive best 10 chunks
    bm25_top_chunks = bm25.get_top_n(tokenized_query, chunks, n=t_chunks_limit)

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
    top_hybrid_chunks = [doc for doc, score in ranked_docs[:top_k]]

    # 2.2 Matching each chunk to its page number from the metadata
    chunk_to_meta = {c: m for c, m in zip(chunks, metadatas)}

    formatted_context_list = []
    for doc in top_hybrid_chunks:
        meta_info = chunk_to_meta.get(doc, {})
        page_num = (
            meta_info.get("page", "Unknown")
            if isinstance(meta_info, dict)
            else "Unknown"
        )
        formatted_context_list.append(f"[Page {page_num}]:\n{doc}")

    return "\n\n---\n\n".join(formatted_context_list)


def run_hybrid_chat_session(
    pdf_source, user_query
): 

    # Initialize indexes once for the active document
    bm25, collection, chunks, metadatas = initialize_hybrid_index(pdf_source)

    # 2.3 Generate The Answer Using An LLM Based On The Paper
    print("Generating final response from hybrid context...\n")

    # 2.4. Conversation History Initialization
    base_system_prompt = (
        "You are a helpful assistant. Answer questions accurately based ONLY on the "
        "provided context from the pdf. If the answer does not "
        "exist in the context, respond with: 'The answer does not exist in the given pdf'."
    )

    system_prompt = base_system_prompt

    print("\n" + "=" * 60)
    print("Chat session initialized. Type 'exit' to quit.")
    print("=" * 60 + "\n")

    context = retrieve_hybrid_context(user_query, bm25, collection, chunks, metadatas)

    # Append structured message with retrieved context and question
    current_turn_payload = f"""[Context]:{context}
    [Question]:{user_query} """

    
            
    # Create full prompt payload without polluting persistent history with bulky contexts
    messages_to_send = [
        {"role": "system", "content": system_prompt}
    ]

    file_history = load_file_history(pdf_source.name)
    for item in file_history:
         messages_to_send.append({"role": "user", "content": item["query"]})
         messages_to_send.append({"role": "assistant", "content": item["answer"]})

    messages_to_send.append({"role": "user", "content": current_turn_payload})

    # We send the LLM the complete messages along with the context of the current question
    completion = client_ai.chat.completions.create(
        model="nvidia/nemotron-3.5-lightning:free",
        messages=messages_to_send,
        temperature=0.2,
    )

    assistant_reply = completion.choices[0].message.content
    persist_chat_history(pdf_source.name, user_query, assistant_reply, context)

    return assistant_reply, context


if __name__ == "__main__":
    sample_pdf = r"D:\GitProjects\Machine-Learning\Advice For Risk Associated with Cultured Meat.pdf"
    sample_query = """
   """

    # run_hybrid_chat_session(sample_pdf, sample_query, chat_history)
