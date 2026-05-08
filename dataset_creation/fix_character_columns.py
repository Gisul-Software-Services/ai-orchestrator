"""
Fix schemas in RAG MongoDB that have CHARACTER columns without length.
PostgreSQL treats CHARACTER (no length) as CHAR(1) which causes
'value too long for type character(1)' errors during validation.

Fix: Replace CHARACTER → VARCHAR(255), CHARACTER VARYING → VARCHAR(255)
"""
import requests

RAG_URL = "http://103.173.99.217:7003"
ADMIN_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"


def fix_character_types(schema: dict) -> tuple[dict, bool]:
    """Fix CHARACTER columns to VARCHAR(255). Returns (fixed_schema, was_changed)."""
    changed = False
    for table_name, table_def in schema.get("tables", {}).items():
        for col in table_def.get("columns", []):
            col_type = col.get("type", "")
            # Fix bare CHARACTER or CHARACTER VARYING without length
            if col_type.upper() in ("CHARACTER", "CHAR"):
                col["type"] = "VARCHAR(255)"
                changed = True
            elif col_type.upper() in ("CHARACTER VARYING", "CHAR VARYING"):
                col["type"] = "VARCHAR(255)"
                changed = True
    return schema, changed


def main():
    print("Fixing CHARACTER columns in RAG MongoDB schemas...")

    # Get all schemas via stats to find domains, then sample
    stats = requests.get(f"{RAG_URL}/api/v1/sql-schemas/stats", timeout=10).json()
    total = stats["total_schemas"]
    print(f"Total schemas: {total}")

    # We need to fetch all schemas — use the select endpoint to sample
    # For a proper fix, we'd need a list-all endpoint
    # For now, fix the known problematic schema
    problematic = [
        "classic_e-commerce_categories",
        "classic_music_album",
    ]

    fixed_count = 0
    for schema_id in problematic:
        # Get schema by selecting with domain
        r = requests.get(
            f"{RAG_URL}/api/v1/sql-schemas/select",
            params={"difficulty": "medium", "sql_category": "join", "limit": 50},
            timeout=10
        )
        # We can't easily get by schema_id via current API
        # The fix needs to be done via re-upload
        print(f"  Schema {schema_id}: needs re-upload with fixed types")

    print("\nTo properly fix: re-upload the curated schemas with CHARACTER → VARCHAR(255)")
    print("Run: python3 dataset_creation/reupload_curated_fixed.py")


if __name__ == "__main__":
    main()
