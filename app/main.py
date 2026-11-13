
import logging

from pydantic import BaseModel
from sqlalchemy.orm import Session
from .redis_client import redis_client
from logger_config import setup_logging
from .database import engine, Base, get_db
from .models import QARecord, chat_with_ai
from fastapi import FastAPI, Depends, HTTPException

# Initialize the robust logging configuration from your custom file
setup_logging()

logger = logging.getLogger(__name__)

# Automatically create database tables on startup (for development/demo purposes)
Base.metadata.create_all(bind=engine)
logger.info("Database tables initialized.")

app = FastAPI(title="Q&A Backend Service", version="1.0.0")
logger.info("FastAPI application started successfully.")

class QuestionRequest(BaseModel):
    question: str

class QAResponse(BaseModel):
    id: str
    question: str
    answer: str
    source: str  # Indicates whether it came from 'cache' or 'generated'

@app.post("/ask", response_model=QAResponse)
def ask_question(payload: QuestionRequest, db: Session = Depends(get_db)):
    question_text = payload.question.strip()
    logger.info(f"Incoming /ask request. Question: '{question_text}'")

    if not question_text:
        logger.warning("Rejected request: Question text is empty.")
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Check Redis cache
    logger.debug("Checking Redis cache for existing answer.")
    cached_answer = redis_client.get(question_text)
    
    if cached_answer:
        logger.info("Cache HIT: Returning answer from Redis.")

        # Cache HIT: Log the query submission in PostgreSQL for audit/analytics history
        db_record = QARecord(question=question_text, answer=cached_answer)
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        logger.debug(f"Audit record saved to PostgreSQL for cache hit. Record ID: {db_record.id}")
        
        return QAResponse(
            id=str(db_record.id),
            question=db_record.question,
            answer=db_record.answer,
            source="cache"
        )
    logger.info("Cache MISS: Initiating AI generation process.")

    # 2. Cache MISS: Generate the answer
    try:
        ai_result = chat_with_ai(question_text)
        answer_text = ai_result.get("response", "Error generating response")
    except Exception as e:
        logger.error(f"Failed during AI generation: {e}")
        raise

    # 3. Save Q&A record in PostgreSQL
    logger.debug("Saving new AI-generated answer to PostgreSQL.")
    db_record = QARecord(question=question_text, answer=answer_text)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    logger.info(f"Successfully saved to database. Record ID: {db_record.id}")

    # 4. Cache the answer in Redis with a 1-hour TTL (3600 seconds)
    logger.debug("Attempting to cache the new answer in Redis.")
    redis_client.setex(question_text, 3600, answer_text)

    logger.info("Request processed successfully. Returning generated response.")
    return QAResponse(
        id=str(db_record.id),
        question=db_record.question,
        answer=db_record.answer,
        source="generated"
    )

@app.delete("/cache")
def clear_redis_cache():
    logger.info("Incoming request to clear Redis cache.")
    
    success = redis_client.clear_cache()
    
    if success:
        logger.info("Cache cleared successfully via API endpoint.")
        return {"status": "success", "message": "Redis cache cleared successfully."}
    else:
        logger.error("Failed to clear cache via API endpoint.")
        raise HTTPException(
            status_code=500, 
            detail="Failed to clear cache or cache is currently disabled."
        )