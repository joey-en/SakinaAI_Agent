from openai import OpenAI

from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

import time
from datetime import datetime

import os
import json
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(".env")
client = OpenAI(
    base_url="https://api.fanar.qa/v1",
    api_key=os.getenv("FANAR_API_KEY"),
)

FOLDER_NAME = "graph_creation"
CHUNK_SIZE = 10000
CHUNK_OVERLAP = 1000
MAX_TOKENS = 1024
SYSTEM_PROMPT_PATH = "./prompts/diagnosis_parser.txt" 

# Load prompt from external file
with open(SYSTEM_PROMPT_PATH, "r", encoding="utf-8") as f:
    SYSTEM_PROMPT = f.read()

def load_document(docu_path):
    ''' returns a loaded TextLoader or PyPDFLoader from the given .txt or .pdf path'''
    file = Path(docu_path)
    extension = file.suffix.lower()

    if extension not in [".txt", ".pdf"]:
        raise ValueError("Only .txt and .pdf files are supported.")

    document = None
    if docu_path.endswith(".txt"):
        loader = TextLoader(docu_path, encoding="utf-8")
        document = loader.load()
    if docu_path.endswith(".pdf"):
        loader = PyPDFLoader(docu_path)
        document = loader.load()
    return document

def split_document_chunks(document):
    ''' returns a list of text chunks from the given document '''
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(document)
    return [chunk.page_content for chunk in chunks]

def load_file_chunks(file_path):
    ''' returns a list of text chunks from the given .txt or .pdf path '''
    document = load_document(file_path)
    return split_document_chunks(document)

def clean_json_string(raw_output: str) -> str:
    ''' attempts to remove all comments from an LLM-generated json '''
    # Remove single-line comments: //, #, --
    no_line_comments = re.sub(r'(?m)(?<!http:)(?<!https:) *(\#|//|--).*$', '', raw_output)

    # Remove multi-line comments like /* ... */
    no_multiline_comments = re.sub(r'/\*.*?\*/', '', no_line_comments, flags=re.DOTALL)

    # Optional: remove trailing commas before closing } or ]
    no_trailing_commas = re.sub(r',\s*}', '}', no_multiline_comments)
    no_trailing_commas = re.sub(r',\s*\]', ']', no_trailing_commas)

    return no_trailing_commas.strip()

def extract_dict_from_chunk(text_chunk: str, retries=3, delay=1.5) -> dict:
    """
    Send a text chunk (e.g., one page) to Fanar to parse into structured JSON.
    Retries on error with exponential backoff.
    """
    user_prompt = f"Extract info from this text:\n\n{text_chunk}\n\n Output only valid JSON with NO COMMENTS."

    for attempt in range(retries):
        try:
            # Asks FANAR to make a JSON based on the text_chunk
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]

            response = client.chat.completions.create(
                model="Fanar",
                messages=messages,
                temperature=0,
                max_tokens=MAX_TOKENS,
            )

            # Cleans the LLM output (removes comments and spaces and ensures proper structure)
            raw_output = response.choices[0].message.content.strip()
            start = raw_output.find("{")
            end = raw_output.rfind("}")
            json_str = raw_output[start:end+1]
            try:
                cleaned = clean_json_string(json_str)
                return json.loads(cleaned)
            except json.JSONDecodeError as e:
                print(f"Failed to decode cleaned output:\n{raw_output}\nError: {e}\n\n\n")
                return None

        except Exception as e:
            print(f"Attempt {attempt+1} failed with error: {e} \n{text_chunk.replace("\n", "").replace("\r", "")[:200]}...")
            time.sleep(delay * (2 ** attempt))

    print("Failed to extract structured data from text chunk after retries.")
    return None

def extract_dict_from_file(file_path: str, notes= "", checkpoint_chunk=20):
    start_time = datetime.now()
    extracted_data = []
    file = Path(file_path)
    filename = file.stem

    # Load chunks using your existing function
    chunks = load_file_chunks(file_path)

    total_chunks = len(chunks)

    # Setup backup folder
    timestamp = datetime.now().isoformat(timespec='seconds').replace(":", "-")
    backup_dir = Path(f"./{FOLDER_NAME}/backup_{filename}_extraction_{timestamp}")
    backup_dir.mkdir(parents=True, exist_ok=True)

    for i, chunk in enumerate(chunks):
        result = extract_dict_from_chunk(chunk)
        extracted_data.append(result)

        if (i + 1) % checkpoint_chunk == 0:
            with open(backup_dir / f"{filename}_backup_{i+1}.json", "w", encoding="utf-8") as f:
                json.dump(extracted_data, f, indent=2)

    # Save final result
    final_name = f"./{FOLDER_NAME}/{filename}_full.json"
    with open(final_name, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, indent=2)

    # Log to extraction metadata
    log_file = Path(f"./{FOLDER_NAME}/extracted_files.json")
    if log_file.exists():
        with open(log_file, "r", encoding="utf-8") as f:
            log = json.load(f)
    else:
        log = []

    log_entry = {
        "file_name": file.name,
        "added_at": datetime.now().isoformat(),
        "number_of_chunks": total_chunks,
        "process_time": str(datetime.now() - start_time),
        "notes" : notes
    }

    log.append(log_entry)
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2)

    return extracted_data, final_name, backup_dir.name, log_entry

extract_dict_from_file("./data/ICD-11.pdf", notes=f"CHUNK_SIZE_{CHUNK_SIZE} CHUNK_OVERLAP_{CHUNK_OVERLAP} MAX_TOKENS={MAX_TOKENS} SYSTEM_PROMPT={SYSTEM_PROMPT}")