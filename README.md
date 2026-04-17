## How it works?

Questions that i asked myself while developing this project that might help others understand the project in a better way.

### How can 2 different titles know they are the same?

Computers dont read words, they see numbers. When you run
```  
ollama.embeddings
```
The AI converts a word like "Bread" into a Vector (a list of 4096 numbers (only in this case because of Llama3)).

We as humans have to think of these numbers as coordinates on a map with 4096 directions.

    "Bread" might be at coordinates: [0.12, 0.88, ...]

    "Baguette" might be at: [0.13, 0.87, ...]

When the code asks Qdrant for a "Similarity Score", it simply measures the distance between those two points. Because the numbers are very close. The math confirms they are about the same thing, even if the spelling is totally different.

### What does Neo4j have to do with Qdrant?

They are two different types of memory working together:

    Qdrant (The Intuition): It handles the "vague" logic. It tells you what something is like. (reason for Qdrant to use a big whiteboard with small dots in "random" places (mathematically calculated))

    Neo4j (The Logic): It handles the "rigid" facts. It tells you how things are connected. (reason for Neo4j to connect using bubbles and connective lines between notes and topics)

To actually explain as a final answer, we use Qdrant to decide which topic name to use, and then use Neo4j to actually draw the line. Without Qdrant, our Neo4j graph would be a complete mess of millions of seperate bubbles that never touch. (dont have any relation)

## Why is Qdrant just dots in a white board?

The "White Board" is a 2D representation of that 4096 dimensional map mentioned earlier. (the reason for us to still use 4096 is to keep it consistent, even if it has nothing to do with Llama3, Qdrant REQUIRES the size ahead of time)
Since we cant see in 4000 directions, Qdrant uses an algorithm (called UMAP or t-SNE) to flatten that map down to a simple X and Y axis.

Here is some articles i found particularly interesting aobut the algorithms [UMAP & t-SNE](https://qdrant.tech/articles/distance-based-exploration/).

The "Dots" are treated as concepts.

    Dots that are somewhat grouped together are  the ones AI considered related to each other.

    Dots far apart are ideas the AI thinks are different.

I guess we could call this "White Board" a "Galaxy of Thoughts". The more notes we add, the more these dots will form clusters (with the same idea, we could call them constellations) representing their different interests.