FROM python:3.13-slim

# Prevent Python from writing .pyc files and enable unbuffered console logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install uv

# Copy all remaining root files (logger_config.py, logging_config.json, .env, README.md) 
# and application source code into the container.
COPY . .

RUN uv pip install --system -e .

# Expose the API port
EXPOSE 8000

# Start the application. 
CMD ["uvicorn", "APIs.API:app", "--host", "0.0.0.0", "--port", "8000"]