"""
Audit the actual sql_schemas collection via the select endpoint.
Sample broadly to get a representative view of all 160 schemas.
"""
import requests, time

RAG_URL = "http://103.173.99.217:7003"
CHAR_TYPES = {"CHARACTER", "CHAR", "CHARACTER VARYING", "CHAR VARYING"}

seen = set()
all_schemas = []

# Sample aggressively across all difficulty/category/domain combos
difficulties = ["easy", "medium", "hard"]
categories = ["select", "join", "aggregation", "subquery", "window", "cte"]

print("Sampling sql_schemas collection...")
for diff in difficulties:
    for cat in categories:
        # Request limit=50 to get more variety per call
        try:
            r = requests.get(
                f"{RAG_URL}/api/v1/sql-schemas/select",
                params={"difficulty": diff, "sql_category": cat, "limit": 50},
                timeout=15
            )
            if r.status_code == 200:
                s = r.json()
                sid = s.get("schema_id")
                if sid and sid not in seen:
                    seen.add(sid)
                    all_schemas.append(s)
        except Exception as e:
            print(f"  Error {diff}/{cat}: {e}")

# Also try domain-specific sampling
domains = ["healthcare", "finance", "retail", "education", "logistics",
           "music", "e-commerce", "sports", "entertainment", "manufacturing"]
for domain in domains:
    for diff in ["medium", "hard"]:
        try:
            r = requests.get(
                f"{RAG_URL}/api/v1/sql-schemas/select",
                params={"difficulty": diff, "sql_category": "join",
                        "domain": domain, "limit": 10},
                timeout=10
            )
            if r.status_code == 200:
                s = r.json()
                sid = s.get("schema_id")
                if sid and sid not in seen:
                    seen.add(sid)
                    all_schemas.append(s)
        except:
            pass

print(f"Sampled {len(all_schemas)} unique schemas out of 160 total\n")

char_schemas = []
no_rel_schemas = []
no_data_schemas = []
source_counts = {}

for s in all_schemas:
    sid = s.get("schema_id", "?")
    tables = s.get("tables", {})
    relationships = s.get("relationships", [])
    sample_data = s.get("sample_data", {})
    source = s.get("source", "unknown")
    source_counts[source] = source_counts.get(source, 0) + 1

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
    has_data = any(
        isinstance(rows, list) and len(rows) > 0
        for rows in sample_data.values()
    )
    if not has_data:
        no_data_schemas.append(sid)

print("=" * 65)
print(f"AUDIT RESULTS ({len(all_schemas)} schemas sampled)")
print("=" * 65)

print(f"\n1. CHARACTER columns (CHAR(1) problem): {len(char_schemas)}")
for sid in char_schemas:
    print(f"   - {sid}")

print(f"\n2. No FK relationships: {len(no_rel_schemas)}")
for sid in no_rel_schemas[:8]:
    print(f"   - {sid}")
if len(no_rel_schemas) > 8:
    print(f"   ... and {len(no_rel_schemas)-8} more")

print(f"\n3. No sample data: {len(no_data_schemas)}")
for sid in no_data_schemas[:5]:
    print(f"   - {sid}")

print(f"\n4. Sources:")
for src, cnt in sorted(source_counts.items(), key=lambda x: -x[1]):
    print(f"   {src:45s}: {cnt}")

print(f"\n{'=' * 65}")
clean = len(all_schemas) - len(set(char_schemas + no_data_schemas))
print(f"  Sampled:          {len(all_schemas)}/160")
print(f"  CHARACTER issues: {len(char_schemas)}")
print(f"  No FK:            {len(no_rel_schemas)} (ok for select/aggregation)")
print(f"  No sample data:   {len(no_data_schemas)}")
print(f"  Clean:            {clean}")
print("=" * 65)
