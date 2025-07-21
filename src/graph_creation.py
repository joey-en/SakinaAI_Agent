import os
from dotenv import load_dotenv
import json

from neo4j import GraphDatabase

def create_kg_entry(tx, entry):
    diagnosis = entry.get("diagnosis")
    # if not diagnosis: return

    aliases = entry.get("aliases", [])
    alias_names = flatten_to_strings(aliases)

    print(diagnosis, alias_names)

    # Create diagnosis node with aliases
    tx.run("""
        MERGE (d:Diagnosis {name: $name})
        SET d.description = $desc, d.aliases = $aliases
    """,
        name=diagnosis,
        desc=" ".join(flatten_to_strings(entry.get("description", []))),
        aliases=alias_names
    )

    for alias in alias_names:
        if alias.lower() != diagnosis.lower():
            tx.run("""
                MERGE (a:DiagnosisAlias {name: $alias})
                WITH a
                MATCH (d:Diagnosis {name: $diagnosis})
                MERGE (a)-[:ALIAS_OF]->(d)
            """, alias=alias, diagnosis=diagnosis)

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

            tx.run("""
                MERGE (d1:Diagnosis {name: $d1})
                MERGE (d2:Diagnosis {name: $d2})
                MERGE (d1)-[:RELATED_TO {note: $note}]->(d2)
            """, d1=diagnosis, d2=related, note=note)

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

    JSON_PATH = "./src./saved_json./DSM_5 Short (cleaned).json"

    # Load cleaned DSM-5 JSON
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        records = json.load(f)

    # Filter out unusable entries ⚠️ TEMPORARY SOLUTION TO IGNORE NULL DIAGNOSIS
    # cleaned_records = [
    #     r for r in records
    #     if isinstance(r, dict) and r.get("diagnosis") and r["diagnosis"].strip() != ""
    # ]
    cleaned_records = records
    
    # Insert into Neo4j
    with driver.session() as session:
        for entry in cleaned_records:
            session.execute_write(create_kg_entry, entry)

    print(f"Loaded {len(cleaned_records)} records to Neo4j.")
    
main()