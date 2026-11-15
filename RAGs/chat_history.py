import json
import os

def persist_chat_history(file_name, user_query, assistant_reply, context, max_items=10, filepath="chat_history.json"):
    entry = {
        "file_name": file_name,
        "query": user_query, 
        "answer": assistant_reply, 
        "rag_context": context
    }
    history_data = []
    
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                history_data = json.load(f)
            except json.JSONDecodeError:
                pass
                
    # Append the new entry
    history_data.append(entry)
    
    # Separate the current file's history from all other files
    other_files_history = [item for item in history_data if item.get("file_name") != file_name]
    current_file_history = [item for item in history_data if item.get("file_name") == file_name]
    
    # Cap the history for the current file to the last 10 questions
    current_file_history = current_file_history[-max_items:]
    
    # Recombine and save to JSON
    history_data = other_files_history + current_file_history
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(history_data, f, indent=4, ensure_ascii=False)

def load_file_history(file_name, filepath="chat_history.json"):
    """Filters and returns up to 10 history items specifically for the requested file."""
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            history_data = json.load(f)
            return [item for item in history_data if item.get("file_name") == file_name]
        except json.JSONDecodeError:
            return []

def clear_all_history(filepath="chat_history.json"):
    """Wipes the entire chat history JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump([], f)

def load_all_history(filepath="chat_history.json"):
    """Retrieves the chat history across all uploaded files."""
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []