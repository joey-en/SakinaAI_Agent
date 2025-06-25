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

PDF_FOLDER_PATH = "./data"
INDEX_PATH = "./saved_index_chunks/faiss.index"
CHUNK_PATH = "./saved_index_chunks/chunks.pkl"

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

def load_pdf_chunks_from_folder(folder_path):
    all_chunks = []
    for filename in os.listdir(folder_path):
        document = load_document(os.path.join(folder_path, filename))
        all_chunks.extend(split_document_chunks(document))
    return all_chunks

# -------

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

# ========== EMBEDDING + FAISS SETUP ==========
import time

def create_embeddings(text_list, batch_size=30, delay=2.0,): # Added batch size because of API limits
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
    if os.path.exists(INDEX_PATH) and os.path.exists(CHUNK_PATH):
        st.info("Loading cached index and chunks...")
        st.session_state['faiss_index'] = load_faiss_index(INDEX_PATH)
        st.session_state['chunks'] = load_chunks(CHUNK_PATH)
        st.success("Cached data loaded.")
    else: # Read folder for the first time
        st.info("Fetching relevant clinical information and building database...")
        chunks = load_pdf_chunks_from_folder(PDF_FOLDER_PATH)
        index, chunk_texts, embeddings = setup_faiss_index(chunks)
        
        if index:
            st.session_state['faiss_index'] = index
            st.session_state['chunks'] = chunk_texts
            st.session_state['embeddings'] = embeddings
            st.info("Index was created sucessfully")

            save_faiss_index(index, INDEX_PATH)
            save_chunks(chunks, CHUNK_PATH)
        else:
            st.error("Failed to build FAISS index.")

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
