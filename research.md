# Task: Containerization, Redis Caching & CI/CD with GitHub Actions

1. Redis in Backend and AI applications
* What is Redis, and how does it work?  
**Redis (Remote Dictionary Server)** is an open-source, in-memory data structure store used as a database, cache, message broker, and streaming engine. It works by keeping all data entirely in RAM rather than relying on slow disk reads, allowing it to perform millions of operations per second with sub-millisecond latencies. While memory-backed, Redis can persist data to disk asynchronously via snapshots (RDB) or append-only logs (AOF).

* Why is Redis commonly used as an in-memory data store?  
**Redis** provides extreme speed and versatile data structures (strings, hashes, lists, sets, sorted sets, bitmaps, and hyperloglogs). Because data lives in RAM, processing throughput is exceptionally high, making it ideal for high-concurrency workloads.

* What is caching, and how does cache expiration (TTL) work?  
**Caching** is the practice of storing copies of frequently accessed or expensive-to-compute data in a faster storage layer (like Redis) to serve subsequent requests instantly.  
**Cache Expiration (TTL - Time-To-Live):** A mechanism that dictates how long a key remains active in Redis before being automatically deleted or evicted. This prevents stale data from lingering indefinitely.

* How can Redis improve backend API performance?  
By offloading heavy database reads, session lookups, and rate-limiting counters to memory. When a client requests data, the backend checks Redis first; if present (a cache hit), it returns the response immediately without hitting the primary SQL database.

* What are Redis use cases in AI applications?  
According to official Redis documentation, key AI use cases include:  
1- **Vector Search:** Storing and indexing vector embeddings (from text, images, or audio) alongside metadata to perform high-speed semantic similarity searches (KNN and range queries) via Redis Search.  
2- **Semantic Caching (LangCache):** Reusing LLM responses for semantically similar prompts to drastically cut API costs and eliminate multi-second generation delays on duplicate or near-duplicate inputs.  
3- **Agent Memory (Agent Memory):** Providing AI agents with two-tier persistent memory—short-term session working memory and long-term semantic recall that survives across interactions.  
4- **Context Management / RAG:** Serving contextual documents and chunks instantly to support Retrieval-Augmented Generation workflows.


* When would you use Redis instead of querying PostgreSQL every time?  
Use Redis when data changes infrequently but is read constantly (e.g., configuration settings, user profiles, product catalogs), when dealing with high-frequency writes that would lock a relational database (e.g., rate limit counters, real-time leaderboards, session tokens), or when executing sub-millisecond vector similarity lookups for AI prompts.
---

2. Docker Compose

* What is Docker Compose?  
A tool defined by Docker for defining and running multi-container Docker applications using a single YAML file (docker-compose.yml).

* Why do we need it when we already have Docker?  
Managing multi-container apps via raw Docker CLI commands requires stringing together separate commands for networks, volumes, environment variables, build flags, and specific startup sequencing (docker network create, docker volume create, docker run ...). Compose lets you define the entire architecture in one declarative file and orchestrate it with a single command (docker compose up).

* What is the difference between `docker run` and `docker compose`?  
provisions and starts a single container interactively or in the background with CLI arguments. docker compose manages multiple containers, networks, and volumes collectively as a unified stack using a declarative configuration file.

* What are services, networks, volumes, and environment variables in Compose?  
    * **Services:** Individual container definitions within the application stack (e.g., a web app, a database, a Redis cache).
    * **Networks:** Isolated communication bridges that allow containers within the same Compose project to talk to each other securely.
    * **Volumes:** Persistent storage mechanisms managed by Docker that survive container teardowns or restarts.
    * **Environment Variables:** Configuration values injected into containers at runtime (e.g., database connection URIs, secret keys).

* How do containers communicate with each other?  
Via Docker networks. When defined in a Compose file, Docker automatically creates a default bridge network for the project. Containers attached to this network can discover and communicate with each other using their service names as hostnames.

* Why should a backend connect to PostgreSQL using the database service name instead of `localhost`?
Inside Docker's networking model, localhost refers exclusively to the container itself—not your host machine or neighboring containers. If your backend container tries to reach PostgreSQL at localhost:5432, it looks inside its own container filesystem/ports. By using the database service name (e.g., postgresql), Docker's embedded DNS server resolves that name to the correct internal container IP address on the shared network.

---

3. Port binding and port mapping

* What is a container port?  
The port inside the isolated container network interface where the application process is actively listening (e.g., FastAPI listening on internal port 8000).

* What is a host port?  
A port on the physical host machine (your laptop or server) exposed to external traffic (e.g., port 8080).

* What does port binding mean?  
The process of mapping a host port to a container port (e.g., -p 8080:8000), telling the Docker daemon to forward any incoming network traffic arriving at the host's port 8080 straight into the container's port 8000.

* What is the difference between `EXPOSE` and `ports` in Docker?  
    * **EXPOSE** (declared in a Dockerfile) is purely documentation/metadata. It informs anyone inspecting the image which port the application listens on, but it does not publish the port to the host machine.

    * **ports** (declared in docker-compose.yml or via docker run -p) actively binds and publishes the port to the host, making it accessible externally.

* How can two containers communicate without publishing their ports to the host?  
By placing them on the same custom or default Docker bridge network. Inter-container communication occurs entirely over internal virtual network interfaces using container service names, bypassing the host machine's public-facing ports entirely for enhanced security.
---

4. Background schedulers and workers
* What is a background task?  
An asynchronous unit of work executed outside the main synchronous HTTP request-response cycle (e.g., sending an email, processing an uploaded image, generating a PDF report) to prevent blocking user requests.

* What is a background worker?  
A dedicated background process or consumer service that continuously polls a queue (like Redis or RabbitMQ) and executes background tasks independently of the web server.

* What is a scheduler?  
A timing mechanism or service responsible for triggering tasks at specific times or intervals (e.g., running a database cleanup every midnight or polling an API every 10 minutes).
---

 5. Dockerfile: Build stage vs Runtime stage
* What is a multi-stage Docker build?  
A pattern in Dockerfiles where multiple FROM instructions are used. Each FROM uses a fresh base image, and you can selectively copy artifacts, binaries, or compiled code from preceding build stages into the final runtime stage, leaving build tools behind.

* What happens during the build stage?  
Heavy build tools, software development kits (SDKs), compilers, package managers, and source code are downloaded and compiled (e.g., compiling a Java application with JDK/Maven or building frontend assets).

* What happens during the runtime stage?  
A clean, lightweight base image (containing only production runtimes, like a JRE or slim Python environment) receives only the finalized compiled artifacts or application code copied from the build stage.

* Why shouldn't compilers and development dependencies be included in production images?  
They bloat image size unnecessarily and increase the security attack surface by introducing unneeded packages and vulnerabilities.

* How does this improve security and image size?  
Dropping compilers, build caches, and dev tools significantly shrinks the final image footprint (often by hundreds of megabytes), which speeds up deployment times, lowers storage costs, and minimizes potential security vulnerabilities.
---

 6. Docker users and permissions
* Why does Docker run containers as root by default in many configurations?  
Historically, Docker was built to execute local developer workloads where root access inside the container simplified permission mapping during development and testing.

* What is the difference between root and a non-root user inside a container?  
**A root user:** possesses ultimate administrative privileges (UID 0), meaning if a process is compromised, the attacker gains full control over the container namespace.  
**A non-root user:** operates with restricted permissions, severely limiting potential damage if an application vulnerability is exploited.

* How do `USER`, `RUN useradd`, and `COPY --chown` work?  
    * **USER:** Switches the active execution context so subsequent instructions (RUN, CMD, ENTRYPOINT) and the running process execute as that specific non-root user.
    * **RUN useradd:** Creates a new system user and group inside the container image.
    * **COPY --chown:** Copies files from the host into the container while explicitly assigning ownership to the specified non-root user/group.

* Why should production containers run as non-root users?   
To enforce the principle of least privilege. If a remote code execution vulnerability occurs in the application, the attacker cannot easily modify system binaries, install malicious packages, or escape containment.

* What problems can happen when a mounted directory has incorrect permissions?  
If a host volume or bind mount is owned by root on the host machine but the container application runs as a non-root user, the containerized app may crash immediately with Permission Denied errors when attempting to read, write, or create files in that directory.

Practical question: How would you create an `appuser` and run a FastAPI application using that user?
```bash
FROM python:3.11-slim

#Create a non-root user and group  
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

WORKDIR /app

#Install dependencies  
COPY requirements.txt .  #or RUN pip install uv
RUN pip install --no-cache-dir -r requirements.txt

#Copy application code with correct ownership  
COPY --chown=appuser:appgroup . /app

#Switch to the non-root user  
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```
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