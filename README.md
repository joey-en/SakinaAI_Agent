# Graph-RAG (GRAG): Embedding-Based Graph Navigation for Mental Health AI

This project builds a structured, semantic knowledge graph from sources like DSM-5 and uses it to support contextual chat interactions — particularly for mental health support.

---

## 1. Creating a Knowledge Graph from DSM-5 (🟢ON-GOING)

The goal here is to turn a structured mental health reference (like DSM-5 or ICD-11) into a navigable knowledge graph.

### How to run

```bash
python graph_creation/document_extraction.py
```

This will generate a JSON file in the following format:

```json
[
  {
    "diagnosis": "Childhood-onset fluency disorder (stuttering)",
    "symptoms": [
      "Sound and syllable repetitions",
      "Sound prolongations of consonants and vowels",
      "Broken words (pauses within a word)",
      "Audible or silent blocking (filled or unfilled pauses in speech)",
      "Circumlocutions (word substitutions to avoid problematic words)",
      "Words produced with an excess of physical tension",
      "Monosyllabic whole-word repetitions"
    ],
    "treatments": null,
    "duration": null,
    "description": [
      "Disturbance in the normal fluency and time patterning of speech.",
      "Interference with academic or occupational achievement or social communication."
    ],
    "related_diagnoses": {
      "Autism Spectrum Disorder": "Not better explained by...",
      "Intellectual Disability (Intellectual Developmental Disorder)": "Not better explained by..."
    }
  }, ...
]
```

### Processing Steps

1. **Parse DSM-5** (🟢ON-GOING)

   * Extract diagnoses and their metadata
   * Identify symptoms, criteria, treatments, duration, description, and related_diagnoses

2. **Build Graph Nodes**

   * Each concept (diagnosis, symptom, treatment) becomes a node

3. **Create Edges**

   * Link nodes (e.g. `GAD --has_symptom→ Restlessness`)

4. **Store Metadata**

   * Descriptions, ICD codes, synonyms, etc.

5. **Embed Nodes**

   * Use `sentence-transformers` to generate vector embeddings
   * Store with FAISS, Annoy, or plain NumPy arrays

### Sample Graph (Text View)

```
Diagnosis: GAD
  ├── has_symptom → Worry
  ├── has_symptom → Restlessness
  ├── has_duration → "6 months"
  ├── treated_by → CBT
```

---

## 2. Chatbot Query Flow

This layer connects the graph to an LLM, turning user queries into meaningful replies using graph traversal.

### Query Flow

```
User → input text
↓
Embed query (SBERT or similar)
↓
Match top nodes using cosine similarity
↓
Traverse nearby nodes (1–2 hops)
↓
Compile info into a prompt
↓
LLM (e.g. FANAR) generates reply
↓
Reply returned and stored in chat history
```

### Example

**User:** “I keep getting panic attacks randomly and I don’t know what to do.”

* Matching nodes:

  * Symptom: Panic Attacks
  * Diagnosis: Panic Disorder
  * Treatments: CBT, Breathing Exercises, SSRIs

* Traversal:

  * Panic Disorder → has\_symptom → Panic Attacks
  * Panic Disorder → treated\_by → CBT, SSRIs
  * Panic Attacks → managed\_by → Breathing Techniques

* LLM prompt (example fragment):

```
User is experiencing frequent panic attacks.

Related context:
- Diagnosis: Panic Disorder
- Treatments: CBT, breathing techniques, medication

Please respond with supportive, informative guidance.
```

### Stored Data

* Chat history
* Node matches and traversal logs
* User-specific context (if any)

---

## 3. Storing and Using Patient Data

This part personalises the chatbot’s behaviour using structured data tied to user records.

### Data Types

| Type            | Storage Format                       | Notes                              |
| --------------- | ------------------------------------ | ---------------------------------- |
| Diagnosis       | Graph: `User123 has_diagnosis → GAD` | Connected to knowledge graph       |
| Symptoms        | Graph: `User123 reports → Fatigue`   | Optionally time-stamped            |
| Journaling logs | Plaintext chunks                     | Can be embedded and indexed        |
| Medications     | Dict or graph                        | Example: `prescribed → Sertraline` |
| Past chats      | JSON / SQLite                        | Used for context memory            |
| Appointments    | Optional calendar system             | External or internal scheduling    |

### Sample Use in Query

**User:** “I don’t think the meds are helping anymore.”

Retrieved context:

* Medication: Sertraline
* Diagnosis: GAD
* Timeline: Started 2 weeks ago

Prompt example:

```
User has been on Sertraline for 2 weeks for GAD. Today they report doubts about its effectiveness.

Generate a supportive reply that acknowledges concerns and offers next-step advice.
```

---

## Data Storage Options

| Component        | Recommended Storage                |
| ---------------- | ---------------------------------- |
| Knowledge Graph  | Neo4j or NetworkX                  |
| Node Embeddings  | FAISS, Annoy, or NumPy             |
| Chat History     | JSON, SQLite, Redis                |
| Patient Profiles | JSON, SQLite, or graph-based model |

---

## Summary: System Overview

| Phase                  | Input              | Process                           | Output                   |
| ---------------------- | ------------------ | --------------------------------- | ------------------------ |
| Graph Creation         | DSM-5              | Parse → Embed → Link              | Graph + embeddings       |
| Chat Handling          | User query         | Embed → Match → Traverse → Prompt | LLM-generated response   |
| Patient Record (Write) | Form or message    | Convert to triples / JSON         | Updated profile/graph    |
| Patient Record (Read)  | User symptom/query | Retrieve from graph/profile       | Context for conversation |

### To launch the app

```bash
streamlit run app.py
```