import json, urllib.request

API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
catalog = json.load(open("/root/gisul_model/aaptor-rag-service/data/sql/catalog.json"))
print("Loaded", len(catalog), "SQL entries")

batch_size = 50
total_upserted = 0
for i in range(0, len(catalog), batch_size):
    batch = catalog[i:i+batch_size]
    payload = json.dumps({"entries": batch}).encode()
    req = urllib.request.Request(
        "http://103.173.99.217:7003/api/v1/ingest/sql",
        data=payload,
        headers={"Content-Type": "application/json", "X-Api-Key": API_KEY},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read())
            upserted = result.get("upserted", 0)
            total_catalog = result.get("total_catalog", 0)
            total_upserted += upserted
            print("Batch", i//batch_size+1, ": upserted=", upserted, "total_catalog=", total_catalog)
    except Exception as e:
        print("Batch", i//batch_size+1, "FAILED:", e)

print("Done. Total upserted:", total_upserted)
