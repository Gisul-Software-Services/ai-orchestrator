"""
Full audit of all 160 schemas — fetch via catalog endpoint (paginated).
"""
import requests

RAG_URL = "http://103.173.99.217:7003"
CHAR_TYPES = {"CHARACTER", "CHAR", "CHARACTER VARYING", "CHAR VARYING"}

# Fetch all schemas via catalog
print("Fetching all schemas via catalog...")
all_schemas = []
offset = 0
limit = 100

while True:
    r = requests.get(
        f"{RAG_URL}/api/v1/catalog/sql",
        params={"limit": limit, "offset": offset},
        timeout=30
    )
    if r.status_code != 200:
        break
    data = r.json()
    entries = data.get("entries", [])
    if not entries:
        break
    all_schemas.extend(entries)
    offset += limit
    if offset >= data.get("total", 0):
        break

print(f"Fetched {len(all_schemas)} schemas\n")

char_schemas = []
no_rel_schemas = []
no_data_schemas = []

for s in all_schemas:
    sid = s.get("schema_id", s.get("_id", "?"))
    tables = s.get("tables", {})
    relationships = s.get("relationships", [])
    sample_data = s.get("sample_data", {})

    # Check 1: CHARACTER columns
    for tname, tdef in tables.items():
        for col in tdef.get("columns", []):
            col_type = col.get("type", "").strip().upper()
            if col_type in CHAR_TYPES:
                char_schemas.append(sid)
                break
        else:
            continue
        break

    # Check 2: No FK relationships
    if not relationships:
        no_rel_schemas.append(sid)

    # Check 3: No sample data
    has_data = any(len(rows) > 0 for rows in sample_data.values() if isinstance(rows, list))
    if not has_data:
        no_data_schemas.append(sid)

print("=" * 65)
print("FULL AUDIT RESULTS (160 schemas)")
print("=" * 65)

print(f"\n1. CHARACTER columns (CHAR(1) problem): {len(char_schemas)}")
for sid in char_schemas[:10]:
    print(f"   - {sid}")

print(f"\n2. No FK relationships: {len(no_rel_schemas)}")
print(f"   (These still work for SELECT/aggregation but not ideal for JOIN)")
for sid in no_rel_schemas[:5]:
    print(f"   - {sid}")
if len(no_rel_schemas) > 5:
    print(f"   ... and {len(no_rel_schemas)-5} more")

print(f"\n3. No sample data: {len(no_data_schemas)}")
for sid in no_data_schemas[:5]:
    print(f"   - {sid}")

print(f"\n{'=' * 65}")
print(f"SUMMARY:")
print(f"  Total schemas:          {len(all_schemas)}")
print(f"  CHARACTER issues:       {len(char_schemas)}")
print(f"  No FK relationships:    {len(no_rel_schemas)}")
print(f"  No sample data:         {len(no_data_schemas)}")
clean = len(all_schemas) - len(set(char_schemas + no_data_schemas))
print(f"  Clean schemas:          {clean}")
print("=" * 65)
