# Task: Containerization, Redis Caching & CI/CD with GitHub Actions

1. Redis in Backend and AI applications
* What is Redis, and how does it work?
* Why is Redis commonly used as an in-memory data store?
* What is caching, and how does cache expiration (TTL) work?
* How can Redis improve backend API performance?
* What are Redis use cases in AI applications?

*When would you use Redis instead of querying PostgreSQL every time?*

---

2. Docker Compose

* What is Docker Compose?
* Why do we need it when we already have Docker?
* What is the difference between `docker run` and `docker compose`?
* What are services, networks, volumes, and environment variables in Compose?
* How do containers communicate with each other?

Why should a backend connect to PostgreSQL using the database service name instead of `localhost`?

---

3. Port binding and port mapping

* What is a container port?
* What is a host port?
* What does port binding mean?
* What is the difference between `EXPOSE` and `ports` in Docker?
* How can two containers communicate without publishing their ports to the host?

---

4. Background schedulers and workers
* What is a background task?
* What is a background worker?
* What is a scheduler?

---

 5. Dockerfile: Build stage vs Runtime stage
* What is a multi-stage Docker build?
* What happens during the build stage?
* What happens during the runtime stage?
* Why shouldn't compilers and development dependencies be included in production images?
* How does this improve security and image size?

---

 6. Docker users and permissions
* Why does Docker run containers as root by default in many configurations?
* What is the difference between root and a non-root user inside a container?
* How do `USER`, `RUN useradd`, and `COPY --chown` work?
* Why should production containers run as non-root users?
* What problems can happen when a mounted directory has incorrect permissions?

Practical question: How would you create an `appuser` and run a FastAPI application using that user?

---

Part 2 — Practical project: Q&A API

-explain why storing Q&A pairs in one table is more appropriate than creating separate question and answer tables for this simple one-to-one relationship.

For a strict one-to-one relationship where a question maps directly to its generated answer, storing both fields in a single table is significantly more appropriate than splitting them into separate questions and answers tables.

Here is why:

**Elimination of Unnecessary JOINs:** In a single-table design, fetching a Q&A pair requires a simple SELECT * FROM qa_records WHERE id = .... Splitting them forces an INNER JOIN on every read, introducing unnecessary computational overhead as your dataset grows.

**Atomic Writes:** Questions and answers are generated and persisted together as a single unit of work. Writing them in a single INSERT statement avoids multi-table transaction management and potential consistency anomalies.

**No Normalization Benefits to Gain:** Database normalization is designed to reduce data redundancy and anomalies (like updating an address in multiple places). Because a question and answer are immutable historical records created together, splitting them provides zero normalization benefits while adding schema complexity (foreign keys, extra constraints).

**Simpler Indexing and Sorting:** If you need to sort history by created_at or search through recent queries, indexing a single table is straightforward and performant.


-If the same question is submitted twice, should the application:

* Create a new PostgreSQL record every time?
* Reuse the existing Q&A record?
* Return the cached answer but still save a separate submission history?

choose a strategy and explain it.

**Recommended Strategy:** Return the cached answer but still save a separate submission history    
* When a Cache Hit occurs, immediately return the cached answer to the user to guarantee sub-millisecond response times.

* Simultaneously, write a new record (or an asynchronous analytics log entry) to PostgreSQL to track that the question was asked again.

**Why this strategy is best:**

1- **Separation of Concerns:**

* **Redis** handles performance and latency reduction (avoiding expensive LLM generation or heavy computations).

* **PostgreSQL** handles audit trails, usage analytics, and history tracking.

2- **Accurate Analytics:** If you only save the first time a question is asked, you lose valuable product telemetry. Knowing how often users ask specific questions helps you identify trending topics, popular queries, or areas where your knowledge base needs expansion.

3- **Resilience:** Even if Redis experiences an outage (handled via a graceful fallback), PostgreSQL safely absorbs the traffic and maintains a complete history of every interaction.