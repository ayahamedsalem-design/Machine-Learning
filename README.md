# Modular AI FastAPI Project

Containerized REST API built with **FastAPI**. This project demonstrates scalable routing, environment configuration, and seamless integration with **OpenRouter AI** for chat completions. It is fully Dockerized and uses `uv` for fast dependency management.

## Features
* **Modular Routing:** Clean separation of concerns using FastAPI's `APIRouter`
* **AI Integration:** Includes a chatbot endpoint powered by OpenRouter.
* **Environment Management:** Secure credential loading via `.env`.
* **Containerized:** Ready for production with a lightweight Docker setup.
* **Fast Dependency Management:** Uses `uv` for blazing-fast package installation.

---

## Prerequisites

Before you begin, ensure you have the following installed:
* [Docker Desktop](https://www.docker.com/products/docker-desktop/) (for containerized deployment)
* Python 3.13+ (if running locally without Docker)
* An API Key from [OpenRouter](https://openrouter.ai/)

---

## Environment Setup

Create a `.env` file in the root of your project directory and add your OpenRouter credentials and desired model:

```env
OPENROUTER_API_KEY=your_actual_api_key_here
CHAT_MODEL="nvidia/nemotron-3.5-super-vl:free"
```

---

## Docker Deployment

The application is easily deployable using Docker. Follow these steps from your terminal in the root project directory:

### 1. Build the Image
Build the Docker image using the provided `Dockerfile`. We tag it as `apis:latest`.
```bash
docker build -t apis:latest .
```

### 2. Run the Container
Start the container in detached mode (`-d`), mapping port 8000 on your host to port 8000 in the container.
```bash
docker run -d --name apis-container -p 8000:8000 apis:latest
```

*(Optional) Check the container status and logs:*
```bash
docker ps
docker logs apis-container
```

### 3. Stop and Cleanup
When you are done testing, you can gracefully stop and remove the container.
```bash
docker stop apis-container
docker rm apis-container
```

---

## API Endpoints Overview

By default, the API runs on `http://127.0.0.1:8000`

**GET Routes:**
* `GET /` - Root endpoint, returns a welcome message.
* `GET /items` - Retrieves all mock items from the database.
* `GET /items/{item_id}` - Retrieves a specific item by its ID.

**POST Routes:**
* `POST /chat` - Sends a prompt to the configured AI model and returns the response.

---

## Usage Example: AI Chat Endpoint

Here is an example of how to interact with the `/chat` endpoint, similar to testing in Postman.

### Request

**Method:** `POST`
**URL:** `http://127.0.0.1:8000/chat`
**Headers:** `Content-Type: application/json`

**Body (JSON):**
```json
{
  "message": "what is docker?"
}
```

### Expected Response

```json
{
  "response": "**Docker** is an open-source platform for developing, shipping, and running applications inside **containers**.\n\nThe core idea: containers\nA container is a lightweight, standalone package that includes everything an application needs to run: the code, runtime, system tools, libraries, and configuration files..."
}
```