import os

from RAGs.extract_and_chunk_pdf import initialize_api

client_ai = initialize_api()

CHAT_MODEL = os.getenv("CHAT_MODEL")

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
        model=CHAT_MODEL,
        messages=messages_to_send,
        temperature=0.3,
    )

    return completion.choices[0].message.content
