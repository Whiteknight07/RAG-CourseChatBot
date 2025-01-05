from langchain_community.graphs import Neo4jGraph


# Replace these with your Neo4j Aura details
uri = "neo4j+s://73e4fccf.databases.neo4j.io"
username = "neo4j"
password = "gA1w286ib8n3AYtS0ILcvhlORTe-wzV6ZBHL_yZKe8E"

# Initialize Neo4jGraph
try:
    kg = Neo4jGraph(url=uri, username=username, password=password, database="neo4j")
    print("Connected successfully to Neo4j Aura!")
except Exception as e:
    print("Error connecting to Neo4j Aura:", e)
