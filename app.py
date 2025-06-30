import os
import streamlit as st
import faiss
import numpy as np
from mistralai import Mistral, UserMessage

# ========== CONFIG ==========
from dotenv import load_dotenv

load_dotenv(".env")
api_key = os.getenv("MISTRAL_API_KEY", "MISTRAL_API_KEY not found")
client = Mistral(api_key=api_key)

DOCUMENT_FOLDER = "./data"
INDEX_PATH = "./database/faiss.index"
CHUNK_PATH = "./database/chunks.pkl"
READ_FILE_LIST = "./database/read_files.json"

# ========== CONTENT LOADING ==========
from langchain.document_loaders import PyPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter

def load_document(docu_path):
    document = None
    if docu_path.endswith(".txt"):
        loader = TextLoader(docu_path, encoding="utf-8")
        document = loader.load()
    if docu_path.endswith(".pdf"):
        loader = PyPDFLoader(docu_path)
        document = loader.load()
    return document

def split_document_chunks(document):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ".", " "]
    )
    chunks = splitter.split_documents(document)
    return [chunk.page_content for chunk in chunks]

def load_file_chunks(file_path):
    document = load_document(file_path)
    return split_document_chunks(document)

def load_datafolder_chunks(folder_path):
#     all_chunks = []
#     for filename in os.listdir(folder_path):
#         all_chunks.extend(load_file_chunks(os.path.join(folder_path, filename)))
#     return all_chunks
    return [chunk for file in os.listdir(folder_path) for chunk in load_file_chunks(os.path.join(folder_path, file))]

import pickle

def save_faiss_index(index, path=INDEX_PATH):
    faiss.write_index(index, path)

def load_faiss_index(path=INDEX_PATH):
    return faiss.read_index(path)

def save_chunks(chunks, path=CHUNK_PATH):
    with open(path, "wb") as f:
        pickle.dump(chunks, f)

def load_chunks(path=CHUNK_PATH):
    with open(path, "rb") as f:
        return pickle.load(f)

import json
from datetime import datetime

def load_read_files(path=READ_FILE_LIST):
    ''' returns a list of read files based on path'''
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return {}

def save_read_files(seen_files, path=READ_FILE_LIST):
    ''' saves a list of read files on the specified file path'''
    with open(path, "w") as f:
        json.dump(seen_files, f, indent=2)
        
def add_read_file(read_files, file_name):
    read_files[file_name] = {"added_at": datetime.now().isoformat()}

def get_new_files(seen_files, document_folder = DOCUMENT_FOLDER):
    ''' returns a list of files in the speficied folder but not in seen_files'''
    all_files = [f for f in os.listdir(document_folder) if f.endswith((".pdf", ".txt"))]
    return [f for f in all_files if f not in seen_files]


# ========== EMBEDDING + FAISS SETUP ==========
import time

def create_embeddings(text_list, batch_size=30, delay=2.0): # Added batch size because of API limits
    all_embeddings = []
    list_size = len(text_list)

    many_chunks = list_size > 100
    if many_chunks: progress_bar = st.progress(0, text=f"Embedding {list_size} chunks in progress...")
    
    try:
        for i in range(0, list_size, batch_size):
            batch = text_list[i:i + batch_size]
            response = client.embeddings.create(model="mistral-embed", inputs=batch)
            embeddings = [r.embedding for r in response.data]
            all_embeddings.extend(embeddings)

            if many_chunks:
                time.sleep(delay) # Delay to avoid rate limit
                percent_done = min((i + batch_size), list_size) / list_size
                progress_bar.progress(percent_done, text=f"Embedding: {i} of {list_size} chunks ({int(percent_done * 100)}%) ")

        if many_chunks: progress_bar.empty() # Remove bar
        return np.array(all_embeddings)
    
    except Exception as e:
        st.error(f"Error in batch {i}–{i+batch_size}: {text_list[i]}... \n\n ------ \n\n {e}")
        return None
    
def setup_faiss_index(text_chunks):
    embeddings = create_embeddings(text_chunks)
    if embeddings is None:
        st.error("Failed to create embeddings. Cannot initialize FAISS index.")
        return None, None, None  # <–– return a tuple regardless of error to avoid more errors
    
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index, chunks, embeddings

def new_document_to_index(new_file_path, index, chunks):
    new_chunks = load_file_chunks(new_file_path)
    new_embeddings = create_embeddings(new_chunks)
    index.add(new_embeddings)
    chunks.extend(new_chunks)

    return index, chunks


# ========== CONTEXT RETRIEVAL ==========

def fetch_relevant_chunks(query, index, chunks, num_chunks=3):
    query_embedding = create_embeddings([query])
    if query_embedding is None:
        return []
    _, indices = index.search(query_embedding, num_chunks)
    return [chunks[i] for i in indices[0]]

# ========== LLM RESPONSE GENERATION ==========

def ask_mistral(context_chunks, query):
    context = "\n".join(context_chunks)
    prompt = (
        f"""
        
        You are a Sakina's supportive mental health assistant. 
        Use the information below to answer the user's concern in a helpful and professional tone. 

        Make sure to greet the user and use emojis when appropriate.
        Default to 1-2 paragraphs responses that are empathetic that radiate curiosity and listening. 
        For every interaction, end by asking questions that will help them respond more personally and effectively.
        
        
        When asked to explain mental health concepts, you can reply with more than 3 paragraphs: 
        start with a high-level overview to empathize, then break the situation or concept into 
        smaller digestable blocks; use analogies if they help.

        ---
        Context:\n{context}\n\n
        ---
        User Query: {query}\n
        ---
        Supportive Response:
        """
    )
    try:
        response = client.chat.complete(
            model="mistral-large-latest",
            messages=[UserMessage(content=prompt)]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error generating response from Mistral: {e}")
        return "Sorry, something went wrong. Please try again."

# ========== STREAMLIT UI ==========

st.set_page_config(page_title="Mental Health Chatbot Sakina Ai", page_icon="🧠")
st.title("🧠 Mental Health Support Chatbot Sakina AI")
st.markdown("_This tool provides general mental health support and is **not** a substitute for professional help. If you're in crisis, please contact a professional or emergency service._")

# Initialize chunks and FAISS index once
if 'chunks' not in st.session_state:

    if not os.path.exists(READ_FILE_LIST):
        with open(READ_FILE_LIST, "w") as f:
            json.dump({}, f)

    seen_files = load_read_files(READ_FILE_LIST)
    new_files = get_new_files(seen_files, DOCUMENT_FOLDER)

    # === Make content DB ======
    if not os.path.exists(INDEX_PATH) and not os.path.exists(CHUNK_PATH):
        st.info("Building new database...")
        chunks = load_datafolder_chunks(DOCUMENT_FOLDER)
        index, chunk_texts, embeddings = setup_faiss_index(chunks)
        save_faiss_index(index, INDEX_PATH)
        save_chunks(chunks, CHUNK_PATH)
        save_read_files(new_files, READ_FILE_LIST)
        new_files = None

    # === Add new documents to content DB ===
    if new_files:
        st.info(f"Found {len(new_files)} new file(s): {', '.join(new_files)}")
        index = load_faiss_index(INDEX_PATH)
        chunks = load_chunks(CHUNK_PATH)

        for file in new_files:
            file_path = os.path.join(DOCUMENT_FOLDER, file)
            index, chunks = new_document_to_index(file_path, index, chunks)
            add_read_file(seen_files, file)
            st.info(f"{file} is added to index")

        save_faiss_index(index, INDEX_PATH)
        save_chunks(chunks, CHUNK_PATH)
        
        save_read_files(seen_files, READ_FILE_LIST)
        # st.success("New documents added to the index.")

    else:
        st.info("Loading cached index and chunks.")

    # === Step 3: Load final state into Streamlit session ===
    st.session_state['faiss_index'] = load_faiss_index(INDEX_PATH)
    st.session_state['chunks'] = load_chunks(CHUNK_PATH)

# User input
user_query = st.text_input("How are you feeling today, or what would you like support with?")

# Display chatbot response
if st.button("Start Chat"):
    if user_query.strip() and 'faiss_index' in st.session_state:
        context_chunks = fetch_relevant_chunks(user_query, st.session_state['faiss_index'], st.session_state['chunks'])
        if context_chunks:
            answer = ask_mistral(context_chunks, user_query)
            st.markdown(f"**SakinaAI Agent:**\n\n{answer}")
        else:
            st.warning("Sorry, I couldn't find relevant context. Please try again.")
    else:
        st.warning("Please enter something you'd like help with.")
