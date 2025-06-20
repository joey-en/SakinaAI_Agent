import os
import streamlit as st
import faiss
import numpy as np
from mistralai import Mistral, UserMessage

# ========== CONFIG ==========

# Set the API key as an environment variable
os.environ["MISTRAL_API_KEY"] = "P5Ya1Is7YS4AM2dVkBU0KrV9Bz0BU0KU"

# Retrieve the API key using os.getenv() 
api_key = os.getenv("MISTRAL_API_KEY")
client = Mistral(api_key=api_key)

# ========== CURATED MENTAL HEALTH TEXT CHUNKS ==========

mental_health_texts = [
    "When you're feeling overwhelmed, take a few deep breaths. Inhale for 4 seconds, hold for 4, exhale for 4. Repeat slowly to help calm your nervous system.",
    "Talking to someone you trust can relieve emotional pressure. Consider reaching out to a friend, counselor, or support group.",
    "It’s okay to feel sad sometimes. Allow yourself to experience emotions without judgment. Feelings pass like clouds.",
    "Getting quality sleep is essential for mental health. Try a bedtime routine, avoid screens before sleep, and keep your environment quiet and dark.",
    "When anxious thoughts arise, try grounding techniques like naming 5 things you see, 4 you can touch, 3 you can hear, 2 you can smell, 1 you can taste.",
    "Exercise helps release endorphins. A short walk, stretch, or dance break can improve mood and reduce stress.",
    "You’re not alone. Many people struggle with similar feelings. Seeking help is a sign of strength, not weakness.",
    "Practice self-compassion. Speak to yourself the way you’d speak to a friend going through the same thing.",
    "Journaling can help organize thoughts and feelings. Even writing a few lines daily can create emotional clarity.",
    "Try to stay hydrated and eat balanced meals. Physical health supports emotional balance too."
]

# ========== EMBEDDING + FAISS SETUP ==========

def create_embeddings(text_list):
    try:
        response = client.embeddings.create(model="mistral-embed", inputs=text_list)
        return np.array([r.embedding for r in response.data])
    except Exception as e:
        st.error(f"Error creating embeddings: {e}")
        return None

def setup_faiss_index(text_chunks):
    embeddings = create_embeddings(text_chunks)
    if embeddings is None:
        st.error("Failed to create embeddings. Cannot initialize FAISS index.")
        return None
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    return index

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
        f"You are a supportive mental health assistant. Use the context below to help the user with their concern.\n\n"
        f"Context:\n{context}\n\n"
        f"User: {query}\n"
        f"Assistant:"
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

# Initialize FAISS index once
if 'faiss_index' not in st.session_state:
    st.session_state['faiss_index'] = setup_faiss_index(mental_health_texts)
    st.session_state['chunks'] = mental_health_texts

# User input
user_query = st.text_input("How are you feeling today, or what would you like support with?")

# Display chatbot response
if st.button("Start Chat"):
    if user_query.strip():
        context_chunks = fetch_relevant_chunks(user_query, st.session_state['faiss_index'], st.session_state['chunks'])
        if context_chunks:
            answer = ask_mistral(context_chunks, user_query)
            st.text_area("Supportive Response:", value=answer, height=250)
        else:
            st.warning("Sorry, I couldn't find relevant context. Please try again.")
    else:
        st.warning("Please enter something you'd like help with.")
