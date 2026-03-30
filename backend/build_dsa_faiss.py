"""
build_faiss_index.py
====================
One-time script to build FAISS vector index from dsa_enriched.json.

Run this AFTER enrich_dsa.py completes.

What it does:
  - Loads dsa_enriched.json
  - Builds searchable text for each problem (title + description + tags)
  - Embeds all problems using all-MiniLM-L6-v2 (CPU, no GPU needed)
  - Saves dsa_faiss.index — the vector search index
  - Saves dsa_metadata.json — maps index position to problem data

Usage:
    python build_faiss_index.py

Output:
    dsa_faiss.index     — FAISS index file
    dsa_metadata.json   — metadata mapping

Run again whenever dsa_enriched.json is updated with new problems.
Takes ~5 minutes for 2500 problems on CPU.
"""

import json
import os
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
ENRICHED_FILE   = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\dsa_enriched.json"
FAISS_INDEX     = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\dsa_faiss.index"
METADATA_FILE   = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\dsa_metadata.json"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE      = 64
# ──────────────────────────────────────────────────────────────────────────────

print("Loading dependencies...")
from sentence_transformers import SentenceTransformer
import faiss

print(f"Loading enriched dataset...")
with open(ENRICHED_FILE, encoding="utf-8") as f:
    problems = json.load(f)

print(f"Total problems: {len(problems)}")


def build_search_text(problem: dict) -> str:
    """
    Combines title + tags + difficulty + description into one searchable string.
    This is what gets embedded into a vector.
    """
    parts = []

    title = problem.get("title", problem.get("task_id", ""))
    if title:
        parts.append(title)

    tags = problem.get("tags", problem.get("topics", []))
    if tags:
        parts.append(" ".join(tags))

    difficulty = problem.get("difficulty", "")
    if difficulty:
        parts.append(difficulty)

    description = problem.get("problem_description", problem.get("description", ""))
    if description:
        parts.append(description[:300])

    return " ".join(parts)


print("Building search texts...")
search_texts = [build_search_text(p) for p in problems]

print("Building metadata...")
metadata = []
for i, problem in enumerate(problems):
    metadata.append({
        "index":       i,
        "title":       problem.get("title", problem.get("task_id", "")),
        "task_id":     problem.get("task_id", ""),
        "question_id": str(problem.get("question_id", "")),
        "difficulty":  problem.get("difficulty", ""),
        "tags":        problem.get("tags", problem.get("topics", [])),
    })

print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
print("First run downloads ~80MB — subsequent runs are instant")
model = SentenceTransformer(EMBEDDING_MODEL)
print("Model loaded.")

print(f"\nEmbedding {len(search_texts)} problems in batches of {BATCH_SIZE}...")
print("This takes ~5 minutes on CPU...")

embeddings = model.encode(
    search_texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)

print(f"\nEmbedding shape: {embeddings.shape}")
print(f"Embedding dimensions: {embeddings.shape[1]}")

print("\nBuilding FAISS index...")
dimension = embeddings.shape[1]
index = faiss.IndexFlatIP(dimension)
index.add(embeddings.astype(np.float32))
print(f"FAISS index built. Total vectors: {index.ntotal}")

print(f"\nSaving FAISS index to {FAISS_INDEX}...")
faiss.write_index(index, FAISS_INDEX)

print(f"Saving metadata to {METADATA_FILE}...")
with open(METADATA_FILE, "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 60)
print("FAISS index built successfully!")
print(f"   Problems indexed : {index.ntotal}")
print(f"   Dimensions       : {dimension}")
print(f"   Index file       : {FAISS_INDEX}")
print(f"   Metadata file    : {METADATA_FILE}")
print("=" * 60)
print("\nNext: Update api_server.py to use FAISS search")
print("Then copy both files into Docker and push.")