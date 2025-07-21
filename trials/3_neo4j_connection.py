from neo4j import GraphDatabase
import os
from dotenv import load_dotenv

load_dotenv(".env")
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", os.getenv("NEO4J_DSM5_KG_PASS")))

def test_connection():
    with driver.session() as session:
        result = session.run("RETURN 'Connected to Neo4j' AS message")
        for record in result:
            print(record["message"])

test_connection()
