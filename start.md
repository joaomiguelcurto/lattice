docker-compose up -d

cd services/api-go
go run main.go

cd services/worker-python
python worker.py

neo4j$ MATCH (n)-[r]->(t) RETURN n, r, t