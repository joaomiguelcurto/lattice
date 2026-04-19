import redis
import ollama
import time
from neo4j import GraphDatabase
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct, VectorParams, Distance

qc = QdrantClient("localhost", port=6333)

qc.delete_collection(collection_name="lattice_vectors")