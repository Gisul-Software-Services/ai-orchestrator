"""Send SQL catalog to RAG service in batches."""
import json
import urllib.request

RAG_URL = "http://103.173.99.217:7003/api/v1/ingest/sql"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
CATALOG = "/root/gisul_model/dataset_creation/sql_dataset_clean_v2.json"
BATCH_SIZE = 100

with open(CATALOG, encoding="utf-8") as f:
    entries = json.load(f)

print(f"Total entries: {len(entries)}")

for i in range(0, len(entries), BATCH_SIZE):
    batch = entries[i:i + BATCH_SIZE]
    payload = json.dumps({"entries": batch}).encode("utf-8")
    req = urllib.request.Request(
        RAG_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": API_KEY,
        },
        method="POST",
    )
    with urllib.request.urlopen(req) as resp:
        result = json.loads(resp.read())
    print(f"Batch {i//BATCH_SIZE + 1}: upserted={result.get('upserted')} total={result.get('total_catalog')}")

print("Done — SQL catalog ingested and FAISS index rebuilt.")
