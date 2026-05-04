"""
Ingest SQL dataset into the RAG service.
Run from the gisul_model root directory:
  python3 ingest_sql_to_rag.py
"""
import json
import time
import requests

RAG_URL = "http://103.173.99.217:7003/api/v1/ingest/sql"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
DATASET_PATH = "dataset_creation/sql_dataset_final_clean.json"
BATCH_SIZE = 100

headers = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY,
}

print(f"Loading dataset from {DATASET_PATH}...")
with open(DATASET_PATH, encoding="utf-8") as f:
    data = json.load(f)

total = len(data)
print(f"Total entries: {total}")

success = 0
for i in range(0, total, BATCH_SIZE):
    batch = data[i : i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1
    try:
        resp = requests.post(RAG_URL, headers=headers, json={"entries": batch}, timeout=30)
        print(f"Batch {batch_num}/{(total + BATCH_SIZE - 1) // BATCH_SIZE}: {resp.status_code} — {resp.text[:120]}")
        if resp.status_code == 200:
            success += len(batch)
    except Exception as e:
        print(f"Batch {batch_num} failed: {e}")
    time.sleep(0.3)

print(f"\nDone! Ingested {success}/{total} entries.")
