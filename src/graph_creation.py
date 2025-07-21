import os
from dotenv import load_dotenv
import json

from neo4j import GraphDatabase
from rapidfuzz import process, fuzz

from build_diagnosis_map import build_diagnosis_alias_map, save_diagnosis_map, load_diagnosis_map

class DiagnosisNormalizer:
    def __init__(self):
        self.known_diagnoses = {}

    def load_alias_map(self, mapping: dict):
        self.alias_map = {k.lower(): v for k, v in mapping.items()}

    def normalize(self, diagnosis: str) -> str:
        if not diagnosis:
            return ""
        return self.alias_map.get(diagnosis.lower().strip(), diagnosis.strip())

def create_kg_entry(tx, entry, normalizer):
    raw_diganosis_name = entry.get("diagnosis")
    if not raw_diganosis_name: return

    diagnosis = normalizer.normalize(raw_diganosis_name)
    if not diagnosis: return
    
    print(diagnosis, "\t>>>", raw_diganosis_name)

    tx.run("MERGE (d:Diagnosis {name: $name}) SET d.description = $desc",
           name=diagnosis,
           desc=" ".join(flatten_to_strings(entry.get("description", []))))

    for symptom in entry.get("symptoms") or []:
        if symptom:
            tx.run("""
                MERGE (s:Symptom {name: $symptom})
                MERGE (d:Diagnosis {name: $diagnosis})
                MERGE (d)-[:HAS_SYMPTOM]->(s)
            """, symptom=symptom, diagnosis=diagnosis)

    for treatment in entry.get("treatments") or []:
        if treatment:
            tx.run("""
                MERGE (t:Treatment {name: $treatment})
                MERGE (d:Diagnosis {name: $diagnosis})
                MERGE (d)-[:TREATED_BY]->(t)
            """, treatment=treatment, diagnosis=diagnosis)

    duration = flatten_to_strings(entry.get("duration"))
    if duration:
        tx.run("""
            MERGE (dur:Duration {length: $duration})
            MERGE (d:Diagnosis {name: $diagnosis})
            MERGE (d)-[:HAS_DURATION]->(dur)
        """, duration=duration, diagnosis=diagnosis)

    for related, note in (entry.get("related_diagnoses") or {}).items():
        if not note: #if note is null give generic message
            note = "related" 

        if related:
            related_normalized = normalizer.normalize(related)
            
            tx.run("""
                MERGE (d1:Diagnosis {name: $d1})
                MERGE (d2:Diagnosis {name: $d2})
                MERGE (d1)-[:RELATED_TO {note: $note}]->(d2)
            """, d1=diagnosis, d2=related_normalized, note=note)

def flatten_to_strings(value):
    """
    Flattens various input types (str, list, dict, None) into a clean list of strings.
    - Dicts → list of stringified values
    - Lists → stringified elements
    - Strings → list with one item
    - None/empty → []
    """
    if value is None:
        return []

    elif isinstance(value, str):
        return [value.strip()] if value.strip() else []

    elif isinstance(value, dict):
        return [str(v).strip() for v in value.values() if v]

    elif isinstance(value, list):
        flattened = []
        for item in value:
            if isinstance(item, dict):
                flattened.extend([str(v).strip() for v in item.values() if v])
            elif isinstance(item, str) and item.strip():
                flattened.append(item.strip())
            elif item is not None:
                flattened.append(str(item).strip())
        return flattened

    else:
        # Fallback: convert to string
        return [str(value).strip()]

def main():
    # Connect to Neo4j MAKE SURE THE INSTANCE IS RUNNING
    load_dotenv(".env")
    driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", os.getenv("NEO4J_DSM5_KG_PASS")))
    normalizer = DiagnosisNormalizer()

    JSON_PATH    = "./src./saved_json./DSM_5_full.json"
    MAPPING_PATH = "./src/saved_mappings/diagnoses_iso.json"
    create_alias_map = False

    # Load cleaned DSM-5 JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Filter out unusable entries ⚠️ TEMPORARY SOLUTION TO IGNORE NULL DIAGNOSIS
    cleaned_records = [
        r for r in records
        if isinstance(r, dict) and r.get("diagnosis") and r["diagnosis"].strip() != ""
    ]
    
    # Making a diagnosis fuzzy alias map 
    diagnosis_names = list(set(
            r["diagnosis"].strip() for r in cleaned_records
            if isinstance(r.get("diagnosis"), str)
        ))
    
    if create_alias_map:
        alias_map = build_diagnosis_alias_map(diagnosis_names)
        save_diagnosis_map(alias_map, MAPPING_PATH)
    else:
        alias_map = load_diagnosis_map(MAPPING_PATH)
    normalizer.load_alias_map(alias_map)

    # Insert into Neo4j
    with driver.session() as session:
        for entry in cleaned_records:
            session.execute_write(create_kg_entry, entry, normalizer)

    print(f"Loaded {len(cleaned_records)} records to Neo4j.")
    
main()