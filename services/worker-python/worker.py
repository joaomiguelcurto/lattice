import redis
import ollama
import time
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

# Redis acts as an "Inbox". It holds incoming notes from the Go API
# so the Python worker doesnt get overwhelmed if too many notes come at once
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

# database credentials
NEO4J_URI = "bolt://localhost:7687" # apparently using Neo4j "bolt" opens a socket that stays open, 
                                    # keeping the line open for as long as needed (insanely faster than without it)
                                    # in docker i had to setup 2 ports, 7474 for http (the one we use on the browser (Dashboard))
                                    # and 7687 for Bolt (usually only meant for programs to use)
NEO4J_AUTH = ("neo4j", "password")

# Qdrant is our "Spacial Memory" storing concepts as coordinates
qc = QdrantClient("localhost", port=6333)

# initialize the collection. 4096 is the dimension size for Llama 3 embeddings

# HOW MATH WORKS:
# cosine (cos) distance is the math used to calculate the angle between two concepts
try:
    qc.create_collection(
        collection_name="lattice_vectors",
        vectors_config=VectorParams(size=4096, distance=Distance.COSINE),
    )
    print("Qdrant collection ready.")
except:
    print("Qdrant collection already exists.")

# saves the logical relationship to Neo4j
def save_to_graph(content, summary):
    with GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH) as driver:
        with driver.session() as session:
            # Neo4j uses "Cypher" as their language
            # https://neo4j.com/docs/cypher-manual/current/introduction/ 
            # creates a 'Note' and a 'Topic' and links them
            # "MERGE" ensures duplicates are not created
            # if the summary (topic) already exists, Neo4j just draws a line to it
            query = """
            MERGE (n:Note {content: $content})
            MERGE (t:Topic {name: $summary})
            MERGE (n)-[:DISCUSSES]->(t)
            """
            session.run(query, content=content, summary=summary)
            print(f"Saved to Neo4j: Note -> {summary}")

# uses Llama 3 to summarize raw text into a core topic
def process_with_ai(text):
    print(f"\nAI is thinking about: {text}")
    
    response = ollama.generate(
        model='llama3', 
        prompt=f"Summarize this note in one short sentence: {text}"
    )
    
    return response['response'].strip()

print("Worker is online. Waiting for notes from the Go API...")
        
while True:
    # this line 'waits' for a note to appear in the Redis queue
    job = r.blpop("lattice_jobs", timeout=0)
    if job:
        note_text = job[1]
        
        # summarize, ai turns a long note into a short topic string
        topic = process_with_ai(note_text)
        
        # vectorization, turn that topic string into 4096 numbers
        embed_resp = ollama.embeddings(model='llama3', prompt=topic)
        vector = embed_resp['embedding']

        # similarity search, asking Qdrant if any of the existing topics are 'close' in terms of math (REFERENCE TO THE MATH EXPLAINED ABOVE)
        search_result = qc.query_points(
            collection_name="lattice_vectors",
            query=vector,
            limit=1
        ).points  # .points to get the actual list

        # if its closest match is > 85% similar, we use the OLD topic name
        final_topic = topic
        if search_result and search_result[0].score > 0.85:
            final_topic = search_result[0].payload['topic']
            print(f"Smart Link: '{topic}' is similar to existing '{final_topic}'")
        else:
            # if its unique, we save the new coordinates to Qdrant
            qc.upsert(
                collection_name="lattice_vectors",
                points=[PointStruct(
                    id=int(time.time()), 
                    vector=vector, 
                    payload={"topic": topic, "original_note": note_text}
                )]
            )
            print(f"New unique topic stored: {topic}")

        # storage, link the original note to either the old or new topic
        save_to_graph(note_text, final_topic)