"""
Audit all 160 schemas in RAG MongoDB for data quality issues:
1. CHARACTER columns without length (CHAR(1) problem)
2. Schemas with no FK relationships (bad for join questions)
3. Schemas with mismatched column types that can't be joined
4. Tables with no sample data
"""
import requests

RAG_URL = "http://103.173.99.217:7003"
ADMIN_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"

CHAR_TYPES = {"CHARACTER", "CHAR", "CHARACTER VARYING", "CHAR VARYING"}

issues = {
    "char_no_length": [],
    "no_relationships": [],
    "no_sample_data": [],
    "single_table": [],
}

# Sample all schemas across all categories
seen = set()
all_schemas = []

difficulties = ["easy", "medium", "hard"]
categories = ["select", "join", "aggregation", "subquery", "window", "cte"]

print("Fetching schemas from RAG MongoDB...")
for diff in difficulties:
    for cat in categories:
        for _ in range(10):  # sample 10 per combo
            try:
                r = requests.get(
                    f"{RAG_URL}/api/v1/sql-schemas/select",
                    params={"difficulty": diff, "sql_category": cat, "limit": 10},
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

print(f"Fetched {len(all_schemas)} unique schemas\n")

char_schemas = set()
no_rel_schemas = []
no_data_schemas = []
single_table_schemas = []

for s in all_schemas:
    sid = s.get("schema_id", "?")
    tables = s.get("tables", {})
    relationships = s.get("relationships", [])
    sample_data = s.get("sample_data", {})
    table_count = len(tables)

    # Check 1: CHARACTER columns without length
    for tname, tdef in tables.items():
        for col in tdef.get("columns", []):
            col_type = col.get("type", "").strip().upper()
            if col_type in CHAR_TYPES:
                char_schemas.add(sid)

    # Check 2: No FK relationships (bad for join)
    if not relationships:
        no_rel_schemas.append(sid)

    # Check 3: No sample data
    has_data = any(len(rows) > 0 for rows in sample_data.values())
    if not has_data:
        no_data_schemas.append(sid)

    # Check 4: Single table
    if table_count == 1:
        single_table_schemas.append(sid)

print("=" * 65)
print("AUDIT RESULTS")
print("=" * 65)
print(f"\n1. CHARACTER columns (no length) — causes CHAR(1) error:")
print(f"   Count: {len(char_schemas)}")
for sid in list(char_schemas)[:5]:
    print(f"   - {sid}")
if len(char_schemas) > 5:
    print(f"   ... and {len(char_schemas)-5} more")

print(f"\n2. No FK relationships (bad for join/subquery):")
print(f"   Count: {len(no_rel_schemas)}")
for sid in no_rel_schemas[:5]:
    print(f"   - {sid}")
if len(no_rel_schemas) > 5:
    print(f"   ... and {len(no_rel_schemas)-5} more")

print(f"\n3. No sample data:")
print(f"   Count: {len(no_data_schemas)}")
for sid in no_data_schemas[:5]:
    print(f"   - {sid}")

print(f"\n4. Single table schemas:")
print(f"   Count: {len(single_table_schemas)}")
for sid in single_table_schemas[:5]:
    print(f"   - {sid}")

print(f"\n{'=' * 65}")
total_issues = len(char_schemas) + len(no_data_schemas) + len(single_table_schemas)
print(f"Total schemas with issues: ~{total_issues}")
print(f"Schemas sampled: {len(all_schemas)}")
print("=" * 65)
