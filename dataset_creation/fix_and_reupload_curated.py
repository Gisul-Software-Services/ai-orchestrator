"""
Fix CHARACTER columns in curated schemas and re-upload to RAG MongoDB.
PostgreSQL treats CHARACTER (no length) as CHAR(1).
Fix: CHARACTER → VARCHAR(255)
"""
import json
import requests

RAG_URL = "http://103.173.99.217:7003"
ADMIN_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
SCHEMAS_FILE = "/root/gisul_model/dataset_creation/all_schemas_combined.json"

CHAR_FIXES = {
    "CHARACTER": "VARCHAR(255)",
    "CHAR": "VARCHAR(255)",
    "CHARACTER VARYING": "VARCHAR(255)",
    "CHAR VARYING": "VARCHAR(255)",
}


def fix_schema(schema: dict) -> tuple[dict, int]:
    """Fix CHARACTER columns. Returns (fixed_schema, fix_count)."""
    fixes = 0
    for table_def in schema.get("tables", {}).values():
        for col in table_def.get("columns", []):
            col_type = col.get("type", "").strip().upper()
            if col_type in CHAR_FIXES:
                col["type"] = CHAR_FIXES[col_type]
                fixes += 1
    return schema, fixes


def main():
    print("=" * 60)
    print("Fix CHARACTER columns and re-upload curated schemas")
    print("=" * 60)

    with open(SCHEMAS_FILE) as f:
        schemas = json.load(f)

    print(f"\nLoaded {len(schemas)} schemas")

    total_fixes = 0
    fixed_schemas = []
    for schema in schemas:
        fixed, count = fix_schema(schema)
        fixed["source_quality"] = "aaptor_curated"
        fixed["usage_count"] = fixed.get("usage_count", 0)
        fixed_schemas.append(fixed)
        if count:
            total_fixes += count
            print(f"  Fixed {count} columns in {schema['schema_id']}")

    print(f"\nTotal fixes: {total_fixes} columns")

    # Re-upload (upsert — updates existing)
    print("\nRe-uploading to RAG MongoDB...")
    resp = requests.post(
        f"{RAG_URL}/api/v1/import-sql-schemas",
        json={"schemas": fixed_schemas},
        headers={"X-Admin-Api-Key": ADMIN_KEY, "Content-Type": "application/json"},
        timeout=60
    )

    if resp.status_code == 200:
        r = resp.json()
        print(f"  Updated: {r.get('updated', 0)}")
        print(f"  Imported: {r.get('imported', 0)}")
    else:
        print(f"  FAILED: {resp.status_code} - {resp.text[:200]}")
        return

    # Also save fixed version locally
    with open(SCHEMAS_FILE, "w") as f:
        json.dump(fixed_schemas, f, indent=2)
    print(f"\nSaved fixed schemas to {SCHEMAS_FILE}")
    print("\nDone!")


if __name__ == "__main__":
    main()
