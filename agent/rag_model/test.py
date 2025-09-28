import chromadb
from sentence_transformers import SentenceTransformer
import json

# --- CONFIG ---
CHROMA_HOST = "localhost"  # If running locally; use container name if inside Docker Compose
CHROMA_PORT = 8000
MODEL_NAME = "intfloat/multilingual-e5-large"

# --- Connect to Chroma in Docker ---
chroma_client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)

# Get the same collection you populated during embedding
collection = chroma_client.get_collection(name="legal_docs")

num_chunks = collection.count()
print("Number of chunks:", num_chunks)

# --- Load embedding model ---
model = SentenceTransformer(MODEL_NAME)

# --- Your query ---
query = "Quelles sont les conditions de remboursement dans l'assurance santé?"
query_embedding = model.encode([query])[0]

# --- Search ---
results = collection.query(
    query_embeddings=[query_embedding],
    n_results=5,
    include=["documents", "metadatas"]  # ensure we return metadata
)

# --- Print results ---
for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), start=1):
    print(f"\n=== Result {i} ===")
    print("Document:", doc[:500], "...")  # truncate text for readability
    print("Metadata:", json.dumps(meta, indent=2, ensure_ascii=False))
    print("-" * 50)
