import os
from openai import OpenAI
from dotenv import load_dotenv


load_dotenv()
api_key = os.getenv("Embedded_Model_Key")

client_ai = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key, timeout=30)


def summarize_cross_file_history(history_text):
    """Summarizes the provided chat history using the remote Nemotron model."""
    prompt = f"""You are a helpful assistant. Summarize the following chat history covering multiple files. Highlight the main topics discussed, the types of documents analyzed, and the key insights provided:

    [Cross-File History]:
    {history_text}
    """

    messages_to_send = [
        {"role": "system", "content": "You are a helpful AI summarization assistant."},
        {"role": "user", "content": prompt},
    ]

    # Reuse the OpenRouter client_ai and Nemotron lightning model
    completion = client_ai.chat.completions.create(
        model="nvidia/nemotron-3.5-lightning:free",
        messages=messages_to_send,
        temperature=0.3,
    )

    return completion.choices[0].message.content
