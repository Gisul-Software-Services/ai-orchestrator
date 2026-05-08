"""
Generate realistic sample data for Spider schemas that have no sample data.
Uses column names and types to generate contextually appropriate fake data.
Then re-uploads to RAG MongoDB.

Strategy:
- INT/INTEGER columns: sequential IDs or realistic numbers
- VARCHAR/TEXT columns: realistic values based on column name
- REAL/FLOAT/DECIMAL: realistic decimal values
- DATE/TIMESTAMP: recent dates
- BOOLEAN: True/False
"""
import json
import random
import re
import requests
import hashlib
from datetime import datetime, timedelta

RAG_URL = "http://103.173.99.217:7003"
ADMIN_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
PARQUET_FILE = "/root/gisul_model/dataset_creation/spider_schemas.parquet"

# ── Value generators by column name pattern ──────────────────────────────────

FIRST_NAMES = ["Alice", "Bob", "Carol", "David", "Emma", "Frank", "Grace", "Henry", "Iris", "Jack"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Miller", "Davis", "Wilson", "Moore", "Taylor"]
CITIES = ["New York", "London", "Paris", "Tokyo", "Sydney", "Berlin", "Toronto", "Dubai", "Singapore", "Mumbai"]
COUNTRIES = ["USA", "UK", "France", "Japan", "Australia", "Germany", "Canada", "UAE", "Singapore", "India"]
STATUSES = ["active", "inactive", "pending", "completed", "cancelled"]
DEPARTMENTS = ["Engineering", "Marketing", "Sales", "HR", "Finance", "Operations", "Legal", "IT"]
TITLES = ["Manager", "Director", "Engineer", "Analyst", "Coordinator", "Specialist", "Lead", "Associate"]

def generate_value(col_name: str, col_type: str, row_idx: int, table_name: str = "") -> any:
    """Generate a realistic value for a column based on its name and type."""
    name_lower = col_name.lower()
    type_upper = col_type.upper().split("(")[0].strip()

    # Primary key / ID columns
    if name_lower in ("id", f"{table_name.lower()}_id", f"{table_name.lower()}id") or name_lower.endswith("_id") or name_lower.endswith("id"):
        if type_upper in ("INT", "INTEGER", "SMALLINT", "BIGINT"):
            return row_idx + 1

    # Name columns
    if name_lower in ("name", "full_name", "player_name", "team_name", "country_name"):
        return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    if name_lower in ("first_name", "fname"):
        return random.choice(FIRST_NAMES)
    if name_lower in ("last_name", "lname", "surname"):
        return random.choice(LAST_NAMES)

    # Contact
    if "email" in name_lower:
        return f"user{row_idx+1}@example.com"
    if "phone" in name_lower:
        return f"+1-555-{1000+row_idx:04d}"
    if "address" in name_lower:
        return f"{(row_idx+1)*10} Main Street"

    # Location
    if name_lower in ("city", "town", "location"):
        return CITIES[row_idx % len(CITIES)]
    if name_lower in ("country", "nation"):
        return COUNTRIES[row_idx % len(COUNTRIES)]
    if name_lower in ("state", "province", "region"):
        return f"Region {row_idx+1}"
    if "zip" in name_lower or "postal" in name_lower:
        return f"{10001 + row_idx}"

    # Status/type
    if name_lower in ("status", "state", "type", "category"):
        return STATUSES[row_idx % len(STATUSES)]
    if "department" in name_lower or "dept" in name_lower:
        return DEPARTMENTS[row_idx % len(DEPARTMENTS)]
    if "title" in name_lower or "position" in name_lower or "role" in name_lower:
        return TITLES[row_idx % len(TITLES)]

    # Numeric
    if "age" in name_lower:
        return 20 + (row_idx * 7 % 50)
    if "salary" in name_lower or "wage" in name_lower:
        return round(40000 + row_idx * 5000 + random.uniform(0, 1000), 2)
    if "price" in name_lower or "cost" in name_lower or "amount" in name_lower or "total" in name_lower:
        return round(10 + row_idx * 15.5 + random.uniform(0, 100), 2)
    if "score" in name_lower or "rating" in name_lower or "rank" in name_lower:
        return round(1 + (row_idx % 10) * 0.9, 1)
    if "count" in name_lower or "quantity" in name_lower or "num" in name_lower:
        return row_idx * 3 + 1
    if "year" in name_lower:
        return 2020 + (row_idx % 5)
    if "month" in name_lower:
        return (row_idx % 12) + 1
    if "day" in name_lower:
        return (row_idx % 28) + 1

    # Date/time
    if type_upper in ("DATE", "DATETIME", "TIMESTAMP"):
        base = datetime(2022, 1, 1)
        return (base + timedelta(days=row_idx * 45 + random.randint(0, 30))).strftime("%Y-%m-%d")

    # Boolean
    if type_upper in ("BOOLEAN", "BOOL"):
        return row_idx % 2 == 0

    # Type-based fallback
    if type_upper in ("INT", "INTEGER", "SMALLINT", "BIGINT", "TINYINT"):
        return row_idx + 1
    if type_upper in ("REAL", "FLOAT", "DOUBLE", "DECIMAL", "NUMERIC"):
        return round(10.0 + row_idx * 7.3, 2)
    if type_upper in ("TEXT", "VARCHAR", "CHAR", "STRING", "NVARCHAR"):
        # Generic text based on column name
        clean_name = col_name.replace("_", " ").title()
        return f"{clean_name} {row_idx + 1}"

    # Default
    return f"{col_name}_{row_idx + 1}"


def generate_table_data(table_name: str, columns: list, num_rows: int = 5) -> list:
    """Generate sample rows for a table."""
    rows = []
    for i in range(num_rows):
        row = {}
        for col in columns:
            col_name = col.get("name", "")
            col_type = col.get("type", "TEXT")
            if col_name:
                row[col_name] = generate_value(col_name, col_type, i, table_name)
        rows.append(row)
    return rows


def main():
    import pyarrow.parquet as pq

    print("=" * 65)
    print("Generate sample data for Spider schemas")
    print("=" * 65)

    # Load Spider schemas from parquet
    t = pq.read_table(PARQUET_FILE)
    data = t.to_pydict()

    print(f"\nLoaded {t.num_rows} Spider schemas from parquet")

    # Get current schemas from RAG to find which ones need sample data
    print("Checking which schemas need sample data...")

    # Fetch all Spider schemas via select endpoint
    spider_schemas_needing_data = []

    difficulties = ["easy", "medium", "hard"]
    categories = ["select", "join", "aggregation", "subquery", "window", "cte"]
    seen = set()

    # Sample more aggressively — run multiple passes
    for _ in range(5):  # 5 passes to maximize coverage
        for diff in difficulties:
            for cat in categories:
                try:
                    r = requests.get(
                        f"{RAG_URL}/api/v1/sql-schemas/select",
                        params={"difficulty": diff, "sql_category": cat, "limit": 50},
                        timeout=10
                    )
                    if r.status_code == 200:
                        s = r.json()
                        sid = s.get("schema_id", "")
                        if sid and sid not in seen and sid.startswith("spider_"):
                            seen.add(sid)
                            sample_data = s.get("sample_data", {})
                            has_data = any(
                                isinstance(rows, list) and len(rows) > 0
                                for rows in sample_data.values()
                            )
                            if not has_data:
                                spider_schemas_needing_data.append(s)
                except:
                    pass

    print(f"Found {len(spider_schemas_needing_data)} Spider schemas without sample data")

    if not spider_schemas_needing_data:
        print("All Spider schemas already have sample data!")
        return

    # Generate sample data for each
    enriched = []
    for schema in spider_schemas_needing_data:
        tables = schema.get("tables", {})
        sample_data = {}

        for table_name, table_def in tables.items():
            columns = table_def.get("columns", [])
            if columns:
                sample_data[table_name] = generate_table_data(table_name, columns, num_rows=5)

        schema["sample_data"] = sample_data
        # Remove _id field — MongoDB will reject updates that try to modify _id
        schema.pop("_id", None)
        enriched.append(schema)
        print(f"  Generated data for: {schema['schema_id']} ({len(tables)} tables)")

    # Upload enriched schemas
    print(f"\nUploading {len(enriched)} enriched schemas...")
    resp = requests.post(
        f"{RAG_URL}/api/v1/import-sql-schemas",
        json={"schemas": enriched},
        headers={"X-Admin-Api-Key": ADMIN_KEY, "Content-Type": "application/json"},
        timeout=60
    )

    if resp.status_code == 200:
        r = resp.json()
        print(f"  Updated: {r.get('updated', 0)}")
        print(f"  Imported: {r.get('imported', 0)}")
        if r.get("errors"):
            print(f"  Errors: {r['errors'][:3]}")
    else:
        print(f"  FAILED: {resp.status_code} - {resp.text[:200]}")
        return

    print(f"\nDone! {len(enriched)} Spider schemas now have sample data.")


if __name__ == "__main__":
    main()
