import os
import json
import numpy as np
from sentence_transformers import SentenceTransformer
from ingest import ingest_all

STORE_PATH = "chroma_store"
EMBED_MODEL = "all-MiniLM-L6-v2"

# ── tiny vector store (no ChromaDB) ──────────────────────────────────────────

def _store_path(base=STORE_PATH):
    os.makedirs(base, exist_ok=True)
    return base

def _embeddings_file(base=STORE_PATH):
    return os.path.join(base, "embeddings.npy")

def _chunks_file(base=STORE_PATH):
    return os.path.join(base, "chunks.json")


def embed_and_store(chunks, persist_path=STORE_PATH, force_rebuild=False):
    emb_file = _embeddings_file(persist_path)
    chk_file = _chunks_file(persist_path)

    if os.path.exists(emb_file) and os.path.exists(chk_file) and not force_rebuild:
        with open(chk_file) as f:
            existing = json.load(f)
        print(f"Store already has {len(existing)} chunks. Skipping re-embedding.")
        print("Pass force_rebuild=True to rebuild.")
        return

    _store_path(persist_path)
    print(f"Loading embedding model '{EMBED_MODEL}'...")
    model = SentenceTransformer(EMBED_MODEL)

    texts = [c["text"] for c in chunks]
    print(f"Embedding {len(texts)} chunks...")
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    np.save(emb_file, embeddings)
    with open(chk_file, "w") as f:
        json.dump(chunks, f)

    print(f"Saved {len(chunks)} chunks to '{persist_path}'")


def retrieve(query, k=5, persist_path=STORE_PATH):
    emb_file = _embeddings_file(persist_path)
    chk_file = _chunks_file(persist_path)

    if not os.path.exists(emb_file):
        raise FileNotFoundError("Vector store not found. Run embed_and_store() first.")

    model = SentenceTransformer(EMBED_MODEL)
    query_vec = model.encode([query])[0]

    embeddings = np.load(emb_file)
    with open(chk_file) as f:
        chunks = json.load(f)

    # Cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normed = embeddings / np.clip(norms, 1e-10, None)
    query_normed = query_vec / np.linalg.norm(query_vec)
    scores = normed @ query_normed          # higher = more similar
    distances = 1 - scores                  # convert to distance

    top_indices = np.argsort(distances)[:k]

    results = []
    for idx in top_indices:
        results.append({
            "text": chunks[idx]["text"],
            "source": chunks[idx]["source"],
            "chunk_index": chunks[idx]["chunk_index"],
            "distance": round(float(distances[idx]), 4)
        })
    return results


if __name__ == "__main__":
    chunks = ingest_all()
    embed_and_store(chunks)

    test_queries = [
        "What do students say about exams and grading?",
        "Which professor is easy or good for beginners?",
        "What courses have a heavy workload at DePaul?",
    ]

    print("\n--- Retrieval Test ---\n")
    for q in test_queries:
        print(f"Query: {q}")
        results = retrieve(q, k=3)
        for r in results:
            print(f"  [dist={r['distance']} | {r['source']}] {r['text'][:120]}...")
        print()