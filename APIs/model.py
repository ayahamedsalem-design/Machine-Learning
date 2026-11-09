import os
from fastapi import HTTPException
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Creating Openrouter 
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key= os.getenv("OPENROUTER_API_KEY"), 
)

def chat_with_ai(user_message: str):
  try:
        completion = client.chat.completions.create(
            model=os.getenv("CHAT_MODEL"),
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        reply = completion.choices[0].message.content
        return {"response": reply}

  except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

