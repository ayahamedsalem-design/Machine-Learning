<<<<<<< HEAD
# Machine Learning Project
# Q&A Backend Service

A production-ready RESTful API service built with FastAPI that generates answers using OpenRouter AI, caches responses in Redis, and persists all queries in PostgreSQL.

## 🏗️ Project Architecture

The system is designed with a microservices-oriented approach, fully containerized using Docker. 
- **FastAPI (Backend):** The core asynchronous web framework handling incoming REST requests. It is built using a multi-stage Dockerfile and runs securely as a non-root user (`appuser`).
- **PostgreSQL (Database):** Acts as the primary persistent storage and audit log. It records every Q&A transaction, utilizing Docker named volumes (`pgdata`) to ensure data survives container restarts.
- **Redis (Cache):** An in-memory data structure store used to cache AI-generated answers, drastically reducing API latency and LLM costs for repeated questions.
- **OpenRouter AI (LLM):** The external AI provider utilized to generate intelligent answers when a cache miss occurs.
- **Robust Logging:** Centralized logging architecture (`logger_config.py`) that separates standard operational logs (`app.log`) from critical system errors (`errors.log`) using rotating file handlers.

## ⚙️ Environment Variables

Before running the project, create a `.env` file in the root directory with the following variables:

```ini
# External API Configuration
OPENROUTER_API_KEY=your_openrouter_api_key_here
CHAT_MODEL=nvidia/nemotron-3.5-embed-1b:free  # Or any other preferred model

# Database and Cache URLs (Configured for Docker Compose internal network)
DATABASE_URL=postgresql+psycopg2://postgres:postgres@db:5432/qadb
REDIS_URL=redis://redis:6379/0
```
ّّّّّّّ
  
## 🚀 How to Run the Project

The easiest and most reliable way to run the complete stack is using Docker Compose.

1. Clone the repository and navigate to the project root.
2. Ensure your `.env` file is properly configured.
3. Start the application by running:
   ```bash
   docker compose up -d
   ```
4. Docker Compose will automatically wait for PostgreSQL and Redis to be healthy before starting the FastAPI backend.
5. The API will be available at: `http://localhost:8000`

## 🧠 How Caching Works

The application implements a highly efficient caching strategy with graceful degradation:
1. **Cache Look-up:** When a user submits a question, the system first checks Redis.
2. **Cache HIT:** If the answer exists, it is instantly returned. The system asynchronously logs the request into PostgreSQL to maintain an accurate audit history of all questions asked.
3. **Cache MISS:** If the answer is not in Redis, the system queries the OpenRouter AI. The generated answer is saved to PostgreSQL and then cached in Redis.
4. **Expiration (TTL):** Cached items are stored using `setex` with a **1-hour TTL (3600 seconds)** to ensure information remains reasonably fresh without overwhelming the AI model.
5. **Graceful Fallback:** If the Redis container crashes or is unreachable, the system catches the connection error, disables caching temporarily, and continues to serve users flawlessly by relying directly on the AI provider and PostgreSQL.

## 🧪 How to Test the API

You can test the API using tools like Postman, Thunder Client, or simply `curl`.

**Endpoint:** `POST /ask`  
**Payload:**
```json
{
  "question": "What is Docker?"
}
```

**Curl Command:**
```bash
curl -X POST "http://localhost:8000/ask" \
     -H "Content-Type: application/json" \
     -d '{"question": "What is Docker?"}'
```

**Expected Response:**
```json
{
  "id": "c0192177-e7a8-4808-8ba8-d870a710f0b9",
  "question": "What is Docker?",
  "answer": "Docker is an open-source platform that lets you package...",
  "source": "generated" 
}
```

## 🔄 GitHub Actions Pipeline (CI/CD)

The project includes an automated Continuous Integration and Continuous Deployment (CI/CD) pipeline configured in `.github/workflows/docker-publish.yml`.

**Pipeline Workflow:**
1. **Trigger:** The pipeline triggers automatically upon any `push` to the `main` branch.
2. **Checkout:** It checks out the latest source code from the repository.
3. **Authentication:** It securely logs into Docker Hub using encrypted GitHub Repository Secrets (`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`).
4. **Build:** It utilizes Docker Buildx to build the optimized, multi-stage image.
5. **Tag & Push:** It tags the image with both the `latest` tag and the unique commit SHA, then pushes it to the Docker Hub registry.

Users can pull and run the latest published image directly from Docker Hub:
```bash
docker pull your-dockerhub-username/qa-backend:latest
```
