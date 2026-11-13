import os
import uuid
import logging

from openai import OpenAI
from .database import Base
from datetime import datetime
from dotenv import load_dotenv
from fastapi import HTTPException
from logger_config import logging
from sqlalchemy import Column, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID


from logger_config import setup_logging

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("OPENROUTER_API_KEY")

chat_model = os.getenv("CHAT_MODEL")

if not api_key:
    logger.warning("OPENROUTER_API_KEY is missing from environment variables! API calls will fail!")

if not chat_model:
    logger.warning("CHAT_MODEL is not set in environment variables! Using fallback or requests might fail.")

# Creating Openrouter 
logger.debug("Initializing OpenRouter OpenAI client.")
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key= api_key, 
)

class QARecord(Base):
    __tablename__ = "qa_records"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index('idx_qa_records_created_at', 'created_at'),
    )

def chat_with_ai(user_message: str):
  logger.info("Sending prompt to OpenRouter model: ", {chat_model})
  logger.debug("Prompt content: ", {user_message})
  try:
        completion = client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = completion.choices[0].message.content
        logger.info("Successfully received and parsed response from AI model.")
        return {"response": reply}

  except Exception as e:
        logger.error("Failed to fetch response from OpenRouter: ", {str(e)}, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))