from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from .database import engine, Base, get_db
from .models import QARecord, chat_with_ai
from .redis_client import redis_client

# Automatically create database tables on startup (for development/demo purposes)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Q&A Backend Service", version="1.0.0")

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
    if not question_text:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Check Redis cache
    cached_answer = redis_client.get(question_text)
    
    if cached_answer:
        # Cache HIT: Log the query submission in PostgreSQL for audit/analytics history
        db_record = QARecord(question=question_text, answer=cached_answer)
        db.add(db_record)
        db.commit()
        db.refresh(db_record)
        
        return QAResponse(
            id=str(db_record.id),
            question=db_record.question,
            answer=db_record.answer,
            source="cache"
        )

    # 2. Cache MISS: Generate the answer
    ai_result = chat_with_ai(question_text)
    answer_text = ai_result.get("response", "Error generating response")

    # 3. Save Q&A record in PostgreSQL
    db_record = QARecord(question=question_text, answer=answer_text)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)

    # 4. Cache the answer in Redis with a 1-hour TTL (3600 seconds)
    redis_client.setex(question_text, 3600, answer_text)

    return QAResponse(
        id=str(db_record.id),
        question=db_record.question,
        answer=db_record.answer,
        source="generated"
    )