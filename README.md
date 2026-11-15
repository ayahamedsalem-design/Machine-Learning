# Machine Learning Project
# 🧠 Enterprise Global RAG System

Welcome to the **Enterprise Global RAG System**, a state-of-the-art Multi-Architecture Retrieval-Augmented Generation (RAG) platform. This project allows you to seamlessly ingest, process, and query massive amounts of PDF documents across multiple cutting-edge RAG architectures simultaneously from a single unified Interface.

---

## 🚀 Core Features

* **Global Knowledge Base (Upload Once, Query Everywhere)**: All uploaded PDFs are chunked and indexed into centralized ChromaDB collections (`global_basic_collection`, `global_parent_collection`, `global_child_collection`, `global_hybrid_collection`). You can query the entire knowledge base at once without specifying individual file names.
* **Advanced Multi-Query Decomposition**: Automatically breaks down complex, multi-part user questions into individual sub-queries. It retrieves distinct context for each part and synthesizes a comprehensive final answer.
* **Rolling Window Memory**: Maintains the context of the conversation using a customizable rolling window (default: last 5 turns) to prevent LLM context-window overflow, while securely saving the complete chat history to a JSON archive.
* **Cross-File Summarization**: Generate instant executive summaries of your entire conversation history across all uploaded documents using an LLM.
* **Precise Source Citations**: The LLM automatically cites the exact source file and page number (or location) for every fact it provides, directly in its response.
* **Smart De-duplication**: Prevents re-indexing the same PDF file multiple times, saving API costs and storage space.
* **Local Privacy & Cloud LLMs**: Built to seamlessly integrate with local Ollama models (e.g., `llama3.2:1b`, `nomic-embed-text`) alongside OpenRouter APIs (e.g., Nvidia Nemotron).

---

## 🏗️ 7 Supported RAG Architectures

You can easily switch between different RAG strategies from the UI sidebar to compare performance and accuracy:

1. 🔹 **Basic RAG**: Standard dense vector retrieval using standard chunking.
2. 🔹 **Parent-Child (Hierarchical) RAG**: Splits text into large blocks (parents) and small overlapping chunks (children). Searches the children for accuracy, but returns the full parent block to the LLM for maximum context.
3. 🔹 **Hybrid RAG**: Combines Semantic (Dense vector) search with Keyword (Sparse - BM25) search using Reciprocal Rank Fusion (RRF) to ensure no keyword or conceptual meaning is missed.
4. 🔹 **Corrective Parent-Child RAG (CRAG)**: Enhances the Hierarchical RAG by adding an LLM-based grading step. It evaluates every retrieved parent block against the specific sub-query and filters out irrelevant chunks before generation.
5. 🔹 **Corrective Hybrid RAG**: The ultimate pipeline. Evaluates and filters the chunks retrieved from the complex Hybrid RRF pipeline to guarantee 100% relevance.
6. 🔹 **Ext Naive RAG**: External/Legacy pipeline for single-document basic retrieval.
7. 🔹 **Ext Corrective RAG**: External/Legacy pipeline utilizing independent retrieval, grading, and web-search fallback logic.

---

## 🛠️ Technology Stack

* **Language**: Python 3.13
* **UI Framework**: Streamlit
* **Vector Database**: ChromaDB (Persistent) & SQLite-vec
* **Keyword Search**: BM25 (`rank-bm25`)
* **LLM Orchestration**: Local Ollama & OpenRouter (OpenAI SDK)
* **Document Processing**: `pypdf`, `langchain-text-splitters`
* **Dependency Management**: `uv` (Fast Python package installer)
* **Containerization**: Docker & Docker Compose (Multi-stage builds, non-root security)

---

## ⚙️ Prerequisites & Setup

1. **Ollama**: Ensure Ollama is installed on your host machine and running your preferred local models (e.g., `llama3.2:1b`).
2. **Docker Desktop** (Required for containerized deployment).
3. **OpenRouter API Key**: Required for Cloud LLMs and Embeddings.

### Environment Variables (`.env`)
Create a `.env` file in the root directory of the project:
```env
OPENROUTER_API_KEY="your_openrouter_api_key_here"
EMBEDDING_MODEL="nvidia/nemotron-3-embed-1b:free"
CHAT_MODEL="nvidia/nemotron-3.5-super-vl:free"
```

## 🐳 Running with Docker (Recommended)
The project includes a highly optimized multi-stage Dockerfile (using uv for lightning-fast dependency installation) and a docker-compose.yml for isolated, secure deployment.
1. Ensure Docker Desktop is running on your machine.
2. Open your terminal in the project root directory.
3. Build and start the container in detached mode:
```bash
docker compose up -d --build
```
1. Access the application in your browser at:  
**👉 http://localhost:8501**

**Note:** The docker-compose.yml mounts the ./chroma_db_global directory to your host to persist your vector database across container restarts. It also configures OLLAMA_HOST=http://host.docker.internal:11434 to allow the Docker container to seamlessly communicate with your host machine's Ollama instance.

**To stop the application:**
```bash
docker compose down
```
**💻 Running Locally (Terminal / Streamlit)**  
If you prefer to run the project directly on your machine without Docker, follow these steps:

1. **Install** uv (The fast Python package manager):
```bash
pip install uv
```
1. **Create and activate a virtual environment:**
```bash
uv venv
   
   # On Windows:
   .venv\Scripts\activate
   
   # On macOS/Linux:
   source .venv/bin/activate
   ```
1. **Install dependencies:**
```bash
uv pip install -r requirements.txt
```
or
```bash
RUN uv pip install streamlit chromadb ollama openaipypdf rank_bm25 python-dotenv langchain-text-splitters
```

1. **Run the Streamlit application:**
```bash
streamlit run app.py
```

1. The application will automatically open in your default browser at http://localhost:8501.

## 📂 Project Structure
```Plaintext
├── app.py                            # Main Streamlit UI and Routing logic
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Multi-stage Docker build configuration
├── docker-compose.yml                # Docker Compose deployment setup
├── .env                              # API keys and Model configurations
│
├── RAGs/                             # Global RAG Architecture Modules
│   ├── basic_RAG.py                  # Global Basic RAG implementation
│   ├── parent_child_RAG.py           # Global Hierarchical implementation
│   ├── hybrid_RAG.py                 # Global Dense + Sparse (BM25) implementation
│   ├── corrective_parent_child_RAG.py# CRAG applied to Hierarchical chunks
│   ├── corrective_hybrid_RAG.py      # CRAG applied to Hybrid chunks
│   ├── extract_and_chunk_pdf.py      # Standard & Hierarchical chunking engine
│   ├── chat_history.py               # Rolling window memory & JSON persistence
│   ├── history_summarizer.py         # LLM-powered cross-file history summarization
│   ├── RAG_service.py                # Retry mechanism for API robustness
│   └── logger_config.py              # Advanced logging configuration
│
└── RAG/                              # External/Legacy Pipeline Modules
    ├── app_bridge.py                 # Bridge connecting Ext pipelines to UI
    ├── ask.py                        # Ext Naive execution
    ├── ask_crag.py                   # Ext Corrective execution
    ├── rag_common.py                 # Ext shared utilities
    └── memory.py                     # Ext memory management (SQLite)
```

Built for absolute accuracy, robust retrieval, and enterprise-grade performance.

``` code snippet
This README is now fully self-contained in a proper `.md` file block format, highlighting all your architectures, the specific embedding model, and providing clear instructions for both Docker and local setups.
```