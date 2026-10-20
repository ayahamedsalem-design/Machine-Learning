import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key)

config = types.GenerateContentConfig(
    temperature=1.5,
    max_output_tokens=300, 
    system_instruction="You are a smart man, and would like to share fun facts.", 
    top_p=0.95)

response = client.models.generate_content(
    model="gemini-3.5-flash-lite",
    contents="Tell me a fun fact about AI",
    config=config
)

print(response.text)