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

neo4j_driver = GraphDatabase.driver(uri=NEO4J_URI, auth=NEO4J_AUTH)

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

# returns the list of existing topics
def get_existing_topics():
    with neo4j_driver.session() as session:
        result = session.run("MATCH (t:Topic) RETURN t.name AS name")
        return [record["name"] for record in result]
    
# saves the logical relationship to Neo4j        
def save_to_graph(note_text, topic_name):
    with neo4j_driver.session() as session:
        # Neo4j uses "Cypher" as their language
        # https://neo4j.com/docs/cypher-manual/current/introduction/ 
        # creates a 'Note' and a 'Topic' and links them
        # "MERGE" ensures duplicates are not created
        # if the summary (topic) already exists, Neo4j just draws a line to it
        query = """
        MERGE (t:Topic {name: $topic_name})
        CREATE (n:Note {content: $note_content, timestamp: timestamp()})
        MERGE (n)-[:CATEGORIZED_AS]->(t)
        """
        session.run(query, topic_name=topic_name, note_content=note_text)

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
    job = r.blpop(["lattice_jobs", "lattice_queries"], timeout=0)
    if job:
        list_name = job[0]
        content = job[1]
        
        if list_name == "lattice_jobs":
            # get current graph state so AI decide if it uses an existing title or old one
            existing_topics = get_existing_topics()
            topics_str = ", ". join(existing_topics) if existing_topics else "None"
            
            category_prompt = f"""
            You are organizing a knowledge graph. 
            EXISTING TOPICS: {topics_str}
            
            NEW NOTE: "{content}"
            
            Task: Pick the most relevant EXISTING TOPIC for this note. 
            If none of the existing topics fit perfectly, create a NEW one (1-2 words).
            Respond ONLY with the topic name.
            """
            
            # stream=False to get the whole word at once
            topic_resp = ollama.generate(model='llama3', prompt=category_prompt, stream=False)
            ai_suggested_topic = topic_resp['response'].strip().replace(".", "")
            
            # vectorization, turn that topic string into 4096 numbers
            embed_resp = ollama.embeddings(model='llama3', prompt=ai_suggested_topic)
            vector = embed_resp['embedding']

            # similarity search, asking Qdrant if any of the existing topics are 'close' in terms of math (REFERENCE TO THE MATH EXPLAINED ABOVE)
            search_result = qc.query_points(
                collection_name="lattice_vectors",
                query=vector,
                limit=1
            ).points  # .points to get the actual list

            # if its closest match is > 85% similar, we use the OLD topic name
            final_topic = ai_suggested_topic
            if search_result and search_result[0].score > 0.85:
                final_topic = search_result[0].payload['topic']
                print(f"Smart Link: '{ai_suggested_topic}' merged into existing '{final_topic}' (Score: {search_result[0].score:.2f})")
            else:
                # if its unique, we save the new coordinates to Qdrant
                qc.upsert(
                    collection_name="lattice_vectors",
                    points=[PointStruct(
                        id=int(time.time()), 
                        vector=vector, 
                        payload={"topic": final_topic}
                    )]
                )    
                
            print(f"Note saved under topic: {final_topic}")
            # storage, link the original note to either the old or new topic
            save_to_graph(content, final_topic)
            
        elif list_name == "lattice_queries":
            print(f"\n Question Received: {content}")
            
            confidence_threshold = 0.25
            
            # turn the question into a vector
            answer = ollama.embeddings(model='llama3', prompt=content)
            q_vector = answer["embedding"]
            
            # find the top 1 most revelant notes in Qdrant
            results = qc.query_points(
                collection_name="lattice_vectors",
                query=q_vector,
                limit=1
            ).points
            
            # 0.00 to 0.20: random noise or very weak relation
            # 0.30 to 0.60: somewhat related to the topic
            # 0.70 to 0.90: strong match / answering the question
            # 1.00: identical text
            context_notes = []

            if results and results[0].score > confidence_threshold:
                matched_topic = results[0].payload['topic']
                print(f"🎯 Matched Topic: {matched_topic} (Score: {results[0].score:.2f})")
                
                # goes into Neo4j to grab all notes for that topic
                with neo4j_driver.session() as session:
                    graph_result = session.run(
                        "MATCH (t:Topic {name: $name})<-[:CATEGORIZED_AS]-(n:Note) RETURN n.content AS content",
                        name=matched_topic
                    )
                    context_notes = [record["content"] for record in graph_result]
            
            if context_notes:
                context_text = "\n".join(context_notes)
                
                prompt = f"""
                Answer the users question concisely using only the information in the provided notes. 
                Do not add introductory phrases like "Here is what I found" or "Great question." 
                If the answer isn't in the notes, say "Information not found."

                NOTES:
                {context_text}

                QUESTION:
                {content}
                """
                
                final_answer = ollama.generate(model='llama3', prompt=prompt)
                print(f"{final_answer['response']}")
            else:
                print("Couldnt find any relevant notes in your library.")