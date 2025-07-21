# 🧠 Neo4j + Cypher Markdown Guide

## Connecting to Neo4j

In Neo4j Desktop app
* Click on your local instance (e.g. `DSM5_KG`)
* Hit the play button to run the instance

In the terminal
```bash
# You can test the connection by running:
python trials/3_neo4j_connection.py
```

## Viewing your Knowledge Graph

In Neo4j Desktop app
* Click on Tools > Query
* Connect to the instance `DSM5_KG`
* Paste the queries and press play

See all diagnosis nodes
```cypher
MATCH (d:Diagnosis)
RETURN d.name
LIMIT 50
```

See all relationships
```cypher
MATCH (a)-[r]->(b)
RETURN a.name, type(r), b.name
LIMIT 50
```

Show symptoms of a specific diagnosis
```cypher
MATCH (d:Diagnosis {name: "Depression"})-[:HAS_SYMPTOM]->(s:Symptom)
RETURN s.name
```

Find diagnoses for a given symptom
```cypher
MATCH (s:Symptom {name: "Insomnia"})<-[:HAS_SYMPTOM]-(d:Diagnosis)
RETURN d.name
```

See related diagnoses
```cypher
MATCH (d:Diagnosis {name: "Depression"})-[:RELATED_TO]->(rd:Diagnosis)
RETURN rd.name
```

Count how many symptoms each diagnosis has
```cypher
MATCH (d:Diagnosis)-[:HAS_SYMPTOM]->(s:Symptom)
RETURN d.name, COUNT(s) AS numSymptoms
ORDER BY numSymptoms DESC
```

Fuzzy search (if you store alternate names or acronyms)
You’ll need a property like `aliases: ["MDD", "Major Depressive Disorder"]`

```cypher
MATCH (d:Diagnosis)
WHERE "MDD" IN d.aliases
RETURN d.name
```


Match multiple symptoms to a possible diagnosis
Example: User says they have "fatigue", "loss of appetite", and "insomnia"

```cypher
MATCH (s:Symptom)<-[:HAS_SYMPTOM]-(d:Diagnosis)
WHERE s.name IN ["Fatigue", "Loss of appetite", "Insomnia"]
RETURN d.name, COUNT(*) AS matchScore
ORDER BY matchScore DESC
```

---

## Future: RAG Chatbot Queries

Some starter query templates you might call dynamically:

Ask: “What are the treatments for GAD?”
```cypher
MATCH (d:Diagnosis {name: "Generalized Anxiety Disorder"})-[:HAS_TREATMENT]->(t:Treatment)
RETURN t.name
```

Ask: “What else is like PTSD?”
```cypher
MATCH (d:Diagnosis {name: "PTSD"})-[:RELATED_TO]->(rd:Diagnosis)
RETURN rd.name
```

## ⚠️ Danger Zone ⚠️

Delete all nodes and relationships
```cypher
MATCH (n)
DETACH DELETE n
```

Delete specific diagnosis node
```cypher
MATCH (d:Diagnosis {name: "Test Diagnosis"})
DETACH DELETE d
```