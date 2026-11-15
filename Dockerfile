# ==========================================
# Stage 1: Builder
# ==========================================
FROM python:3.13-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered console logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install uv

# Create a virtual environment and install dependencies directly
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# # Install required packages for the RAG System
#  RUN uv pip install streamlit chromadb ollama openai pypdf rank_bm25 python-dotenv langchain-text-splitters

# Copy the requirements file first to leverage Docker cache
COPY requirements.txt .
# Install dependencies from the requirements file
RUN uv pip install -r requirements.txt

# ==========================================
# Stage 2: Runner (Production)
# ==========================================
FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered console logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Activate the virtual environment from the builder stage
ENV PATH="/opt/venv/bin:$PATH"

# Create a non-root user for security purposes
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Force full ownership of the entire /app directory and its contents to appuser
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

# Expose Streamlit port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "app.py", "--server.address", "0.0.0.0", "--server.port", "8501"]