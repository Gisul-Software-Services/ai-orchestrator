"""
build_aiml_faiss.py
====================
One-time script to build FAISS vector index from aiml_dataset_catalog.json.

Run this AFTER adding new datasets to the catalog.

What it does:
  - Loads aiml_dataset_catalog.json
  - Embeds each dataset using all-MiniLM-L6-v2 (CPU, no GPU needed)
  - Saves aiml_faiss.index — the vector search index
  - Saves aiml_catalog_metadata.json — maps index position to dataset info

Usage:
    python build_aiml_faiss.py

Output:
    aiml_faiss.index            — FAISS index file
    aiml_catalog_metadata.json  — metadata mapping

Run again whenever aiml_dataset_catalog.json is updated with new datasets.
Takes < 1 minute even for 500+ datasets on CPU.
"""

import json
import os
import numpy as np

# ── Config ────────────────────────────────────────────────────────────────────
CATALOG_FILE = "/mnt/c/Users/adity/Documents/Gisul/gisul_model/assets/aiml-data/aiml_dataset_catalog.json"
FAISS_INDEX   = "/mnt/c/Users/adity/Documents/Gisul/gisul_model/assets/aiml-data/aiml_faiss.index"
METADATA_FILE = "/mnt/c/Users/adity/Documents/Gisul/gisul_model/assets/aiml-data/aiml_catalog_metadata.json"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
BATCH_SIZE      = 32
# ──────────────────────────────────────────────────────────────────────────────

print("Loading dependencies...")
from sentence_transformers import SentenceTransformer
import faiss

print(f"Loading catalog from {CATALOG_FILE}...")
with open(CATALOG_FILE, encoding="utf-8") as f:
    catalog = json.load(f)

print(f"Total datasets: {len(catalog)}")


def build_search_text(dataset: dict) -> str:
    """
    Combines all meaningful fields into a single searchable string.
    This is what gets embedded into a vector.
    Order matters — most important fields first.
    """
    parts = []

    # Name — most important
    name = dataset.get("name", "")
    if name:
        parts.append(name)

    # Domain
    domain = dataset.get("domain", "")
    if domain:
        parts.append(domain)

    # Category (tabular / nlp / time-series / etc.)
    category = dataset.get("category", "")
    if category:
        parts.append(category)

    # Tags — very important for matching
    tags = dataset.get("tags", [])
    if tags:
        parts.append(" ".join(tags))

    # Use-case — captures what the dataset is used for
    use_case = dataset.get("use_case", "")
    if use_case:
        parts.append(use_case[:200])

    # Description — semantic meaning
    description = dataset.get("description", "")
    if description:
        parts.append(description[:300])

    # Features info (new field — replaces features_description)
    features_info = dataset.get("features_info", "")
    if features_info:
        parts.append(features_info[:150])

    # Target type
    target_type = dataset.get("target_type", "")
    if target_type:
        parts.append(target_type)

    return " ".join(parts)


print("Building search texts...")
search_texts = [build_search_text(d) for d in catalog]

print("Building metadata...")
metadata = []
for i, dataset in enumerate(catalog):
    metadata.append({
        "index":       i,
        "id":          dataset.get("id", ""),
        "name":        dataset.get("name", ""),
        "source":      dataset.get("source", ""),
        "domain":      dataset.get("domain", ""),
        "tags":        dataset.get("tags", []),
        "difficulty":  dataset.get("difficulty", []),
        "target_type": dataset.get("target_type", ""),
        "size":        dataset.get("size", ""),
        "direct_load": dataset.get("direct_load", True),
    })

print(f"\nLoading embedding model: {EMBEDDING_MODEL}")
print("First run downloads ~80MB — subsequent runs are instant")
model = SentenceTransformer(EMBEDDING_MODEL)
print("Model loaded.")

print(f"\nEmbedding {len(search_texts)} datasets...")
embeddings = model.encode(
    search_texts,
    batch_size=BATCH_SIZE,
    show_progress_bar=True,
    convert_to_numpy=True,
    normalize_embeddings=True
)

print(f"Embedding shape: {embeddings.shape}")

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
print("AIML FAISS index built successfully!")
print(f"   Datasets indexed : {index.ntotal}")
print(f"   Dimensions       : {dimension}")
print(f"   Index file       : {FAISS_INDEX}")
print(f"   Metadata file    : {METADATA_FILE}")
print("=" * 60)
print("\nNext: Restart api_server.py — it will auto-load the FAISS index.")