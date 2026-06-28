# Galaxy of Thoughts

A personal knowledge graph that turns your notes into a living, searchable map of ideas - powered by vector embeddings, semantic search, and graph relationships.

---

## What is this?

Every time you add a note, this project does two things: it remembers what the note *means* (not just what it says), and it remembers how that note connects to everything else you have written. Over time, your notes stop being a pile of files and start becoming something closer to a mind map that thinks for itself.

---

## How it works

### How can two different titles know they are the same thing?

Computers do not read words - they see numbers. When you run `ollama.embeddings`, the AI converts a word like "Bread" into a **vector**: a list of 4096 numbers that act like coordinates on a map with 4096 directions.

```
"Bread"    might live at coordinates: [0.12, 0.88, ...]
"Baguette" might live at coordinates: [0.13, 0.87, ...]
```

When the code asks for a "Similarity Score", it simply measures the distance between those two points. Because the numbers are close together, the math confirms they are roughly the same concept -- even if the spelling is completely different.

---

### What does Neo4j have to do with Qdrant?

They are two different types of memory working together.

**Qdrant (The Intuition)** handles vague, fuzzy logic. It answers the question: *what is this similar to?* Think of it as a whiteboard covered in dots scattered across a massive coordinate space.

**Neo4j (The Logic)** handles rigid, factual relationships. It answers the question: *how are these things connected?* Think of it as bubbles and lines, like a traditional mind map.

The two work together like this: Qdrant decides *which topic name* to use, and then Neo4j *draws the line* between nodes. Without Qdrant, the Neo4j graph would become millions of disconnected bubbles that never touch each other. Without Neo4j, you would have similarity scores but no structured relationships to navigate.

---

### Why does Qdrant look like dots on a whiteboard?

That whiteboard is a **2D representation** of the 4096-dimensional coordinate space described above. Since humans cannot see in 4000 directions, Qdrant uses a dimensionality reduction algorithm (UMAP or t-SNE) to flatten that space down to a simple X and Y axis you can actually look at.

Each dot represents a concept. Dots that cluster together are ideas the AI considered related. Dots that are far apart are ideas the AI thinks are different.

The more notes you add, the more these dots form clusters - almost like constellations forming in a night sky. That is where the name comes from: this is your **Galaxy of Thoughts**. Each cluster is a constellation of related ideas, and the whole map grows with you over time.

If you want to go deeper on how UMAP and t-SNE work under the hood, [this article from Qdrant](https://qdrant.tech/articles/distance-based-exploration/) is a great read.

---

## Tech Stack

| Tool | Role |
|------|------|
| **Ollama + Llama3** | Generates vector embeddings (4096 dimensions) |
| **Qdrant** | Stores and searches vectors by similarity |
| **Neo4j** | Stores and queries relationships between concepts |

---

## Getting Started

_Add your setup steps here._

---

## Why 4096 dimensions?

That number comes from Llama3, the model used to generate the embeddings. Qdrant requires the vector size to be defined upfront and kept consistent, so 4096 is locked in across the whole project -- even in parts that have nothing to do with Llama3 directly.
