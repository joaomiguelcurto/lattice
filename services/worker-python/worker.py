import redis
import ollama
import time

# connect to Redis "Memo Pad"
# use 'localhost' and '6379' just like in Go
r = redis.Redis(host='localhost', port=6379, decode_responses=True)

def process_with_ai(text):
    print(f"\nAI is thinking about: {text}")
    
    # ask ollama to summarize the note
    # this shows the AI the 'memo' Go left behind
    response = ollama.generate(
        model='llama3', 
        prompt=f"Summarize this note in one short sentence: {text}"
    )
    
    return response['response']

print("Worker is online. Waiting for notes from the Go API...")

# infinite loop for "listening"
while True:
    # blpop (Blocking Left Pop) pulls the oldest 'memo' out of the tube
    # it waits here until Go pushes something into "lattice_jobs"
    job = r.blpop("lattice_jobs", timeout=0)
    
    if job:
        # job[1] is the text content
        note_text = job[1]
        summary = process_with_ai(note_text)
        print(f"Summary: {summary}")