# Machine Learning Project

A Python utility that summarizes PDF or plain text files using local Large Language Models via **Ollama**.

---

## Features
- **Local & Private:** Runs entirely on your local machine using Ollama.
- **Multiple Formats:** Supports both `.pdf` and `.txt` documents.
- **Terminal Progress Tracking:** Visual feedback while generating summaries.

---

## Prerequisites

1. **Install Ollama:**
   Download and install from [ollama.com](https://ollama.com).

2. **Pull a Model:**
   ```bash
   ollama run llama3.2

3. **Install Python Dependencies:**
    ```Bash
    pip install ollama pypdf
    Project Structure

## How to Run
1. Clone or download this repository.
2. Run the script:
    ```Bash
    python file_summarizer.py
3. Custom File Input
    By default, the script reads Cave.pdf relative to the script directory. To summarize a different file:
    Open file_summarizer.py and uncomment the input line
    ```Python
    # target_file = input("Enter file path: ").strip("\"'")