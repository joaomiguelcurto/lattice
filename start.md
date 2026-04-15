docker-compose up -d

cd services/api-go
go run main.go

cd services/worker-python
python worker.py

curl -X POST http://localhost:8080/ingest -d "content=Artificial intelligence is transforming how we organize personal knowledge by automating the process of linking ideas."