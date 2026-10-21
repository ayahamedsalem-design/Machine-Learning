import os
from pathlib import Path
from pypdf import PdfReader
import ollama

# Reading File Function
def extract_text_from_file(file_path: str) -> str:
    """Extract text from Files type .txt or .pdf"""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"The File doesn't exist in this path  : {file_path}")

    _, ext = os.path.splitext(file_path)
    ext = ext.lower()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()

    elif ext == ".pdf":
        reader = PdfReader(file_path)
        extracted_text = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                extracted_text.append(text)
        return "\n".join(extracted_text)

    else:
        raise ValueError("File format not supported please choose file type .txt or .pdf")

# Summarize Function
def summarize_content(text: str, model: str = "llama3.2") -> str:
    """To summarize send the content to Ollama model"""
    if not text.strip():
        return "The File is empty or doesn't have readable text."
    print(f" Reading and Summarizing the file text size: {len(text)} characters")

    system_prompt = (
        "أنت مساعد محترف في تحليل وتلخيص المستندات. "
        "قم بتلخيص المحتوى التالي باللغة العربية بأسلوب منظم وواضح: "
        "ابدأ بنبذة عامة سريعة، ثم اذكر أهم النقاط والنتائج في نقاط محددة (Bullet points)."
    )

    response = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is file that needs to be summarized:\n\n{text}"}
        ],
        options={
            "temperature": 0.2  # High focus and precision
        }
    )

    return response["message"]["content"]



if __name__ == "__main__":

    target_file = Path(__file__).resolve().parent / "Cave.pdf"
    #target_file = input("Enter file path: ")

    try:
        content = extract_text_from_file(target_file)
        summary = summarize_content(content)
        
        print("\n" + "="*40)
        print("Summary Result:")
        print("="*40)
        print(summary)
        
    except Exception as e:
        print(f"An Error Occurred: {e}")