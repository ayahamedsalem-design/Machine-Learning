import os
import logging

from openai import OpenAI
from dotenv import load_dotenv
from fastapi import HTTPException
from logger_config import setup_logging

load_dotenv()

logger = logging.getLogger(__name__)

api_key = os.getenv("OPENROUTER_API_KEY")

chat_model = os.getenv("CHAT_MODEL")

if not api_key:
    logger.warning("OPENROUTER_API_KEY is missing from environment variables!")

if not chat_model:
    logger.warning("CHAT_MODEL is not set in environment variables! Model requests might fail.")

# Creating Openrouter 
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key= api_key, 
)

def chat_with_ai(user_message: str):
  logger.info("Sending prompt to OpenRouter model: %s", chat_model)
  logger.debug("Prompt content: %s", user_message)
  try:
        completion = client.chat.completions.create(
            model=chat_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = completion.choices[0].message.content
        logger.info("Successfully received response from OpenRouter.")
        return {"response": reply}

  except Exception as e:
        logger.error("Failed to fetch response from OpenRouter: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

