
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

# Install required packages
RUN uv pip install fastapi uvicorn sqlalchemy psycopg2-binary redis pydantic openai python-dotenv

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

# WORKDIR /app

# # Copy the virtual environment from the builder stage
# COPY --from=builder /opt/venv /opt/venv

# # Copy application code and change ownership to the non-root user
# COPY --chown=appuser:appuser . .

# # Create logs directory and give ownership to appuser BEFORE switching user
# RUN mkdir -p logs && chown -R appuser:appuser logs

# # Switch to the non-root user
# USER appuser

# EXPOSE 8000

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
WORKDIR /app

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application code
COPY . .

# Force full ownership of the entire /app directory and its contents to appuser
RUN chown -R appuser:appuser /app

# Switch to the non-root user
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

