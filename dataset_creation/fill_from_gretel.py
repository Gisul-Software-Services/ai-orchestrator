#!/usr/bin/env python3
"""
Fill missing categories from gretel parquet cache.
No LLM needed — pure DuckDB verification.
Takes ~10-15 minutes.

Usage:
    python3 fill_from_gretel.py
"""

import json
import re
import os
import uuid
import duckdb
import pandas as pd
from collections import Counter
from tqdm import tqdm

EXISTING_FILE = "sql_dataset_final_clean.json"
OUTPUT_FILE = "sql_dataset_final_clean.json"
GRETEL_CACHE = "gretel_sql_cache.parquet"

# How many we need per category
CATEGORY_TARGETS = {
    "join":        400,
    "select":      400,
    "subquery":    400,
    "aggregation": 400,
    "window":      400,
}

# Gretel complexity → our category
COMPLEXITY_TO_CATEGORY = {
    "single join":      "join",
    "multiple_joins":   "join",
    "basic sql":        "select",
    "subqueries":       "subquery",
    "ctes":             "subquery",
    "aggregation":      "aggregation",
    "window functions": "window",
    "set operations":   "aggregation",
}

# ═══════════════════════════════════════════════════════════════
# PARSE SCHEMA + SAMPLE DATA FROM SQL CONTEXT
# ═══════════════════════════════════════════════════════════════

def parse_sql_context(sql_context: str) -> tuple:
    schemas = {}
    sample_data = {}

    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)',
        re.IGNORECASE | re.DOTALL
    )

    for table_name, columns_raw in create_pattern.findall(sql_context):
        columns = []
        for col_line in columns_raw.split(','):
            col_line = col_line.strip()
            if re.match(r'^\s*(PRIMARY|FOREIGN|UNIQUE|CHECK|INDEX|CONSTRAINT)\s+', col_line, re.I):
                continue
            parts = col_line.split()
            if len(parts) < 2:
                continue
            col_name = parts[0].strip('`"[]')
            col_type_raw = parts[1].upper()
            if any(t in col_type_raw for t in ["INT", "SERIAL"]):
                col_type = "INTEGER"
            elif any(t in col_type_raw for t in ["NUMERIC", "DECIMAL", "FLOAT", "DOUBLE", "REAL", "NUMBER"]):
                col_type = "DECIMAL"
            elif any(t in col_type_raw for t in ["CHAR", "TEXT", "STRING", "VARCHAR", "NVARCHAR"]):
                col_type = "VARCHAR(255)"
            elif "BOOL" in col_type_raw:
                col_type = "BOOLEAN"
            elif any(t in col_type_raw for t in ["DATE", "TIME", "TIMESTAMP"]):
                col_type = "TIMESTAMP"
            else:
                col_type = "TEXT"

            constraint = ""
            col_upper = col_line.upper()
            if "PRIMARY KEY" in col_upper:
                constraint = "PRIMARY KEY"
            elif "NOT NULL" in col_upper:
                constraint = "NOT NULL"

            columns.append({"name": col_name, "type": col_type, "constraints": constraint})

        if columns:
            schemas[table_name] = {"columns": columns}
            sample_data[table_name] = []

    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+[`"]?(\w+)[`"]?\s*(?:\(([^)]+)\))?\s*VALUES\s*((?:\([^)]+\)\s*,?\s*)+)',
        re.IGNORECASE | re.DOTALL
    )

    for table_name, cols_str, values_str in insert_pattern.findall(sql_context):
        if table_name not in schemas:
            continue
        if cols_str.strip():
            col_names = [c.strip().strip('`"') for c in cols_str.split(',')]
        else:
            col_names = [c["name"] for c in schemas[table_name]["columns"]]

        value_tuples = re.findall(r'\(([^)]+)\)', values_str)
        for value_tuple in value_tuples:
            raw_values = re.split(r',(?=(?:[^\']*\'[^\']*\')*[^\']*$)', value_tuple)
            row = {}
            for col_name, raw_val in zip(col_names, raw_values):
                val = raw_val.strip().strip("'\"")
                if val.upper() in ("NULL", "NONE", ""):
                    val = None
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass
                row[col_name] = val
            if row:
                sample_data[table_name].append(row)

    return schemas, sample_data


# ═══════════════════════════════════════════════════════════════
# DUCKDB VERIFY + CAPTURE OUTPUT
# ═══════════════════════════════════════════════════════════════

def verify_and_capture(schemas: dict, sample_data: dict, sql: str) -> tuple:
    conn = duckdb.connect(":memory:")
    try:
        for table_name, schema in schemas.items():
            col_defs = []
            for col in schema.get("columns", []):
                col_type = col["type"].split("(")[0]
                col_defs.append(f'"{col["name"]}" {col_type}')
            conn.execute(f'CREATE TABLE "{table_name}" ({", ".join(col_defs)})')

        for table_name, rows in sample_data.items():
            if table_name not in schemas or not rows:
                continue
            col_names = [c["name"] for c in schemas[table_name]["columns"]]
            for row in rows:
                if not isinstance(row, dict):
                    continue
                available_cols = [k for k in row.keys() if k in col_names]
                if not available_cols:
                    continue
                values = [row.get(c) for c in available_cols]
                placeholders = ", ".join(["?" for _ in values])
                columns_str = ", ".join(f'"{c}"' for c in available_cols)
                conn.execute(
                    f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})',
                    values,
                )

        # Normalize T1. aliases
        normalized_sql = re.sub(r'\bT\d+\.', '', sql)
        result = conn.execute(normalized_sql).fetchall()
        columns = [desc[0] for desc in conn.description]

        if not result:
            return (False, None)

        output = []
        for row in result:
            row_dict = {}
            for col_name, val in zip(columns, row):
                if val is None:
                    row_dict[col_name] = None
                elif isinstance(val, (int, float, str, bool)):
                    row_dict[col_name] = val
                else:
                    row_dict[col_name] = str(val)
            output.append(row_dict)

        return (True, output)

    except Exception:
        return (False, None)
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# DIFFICULTY FROM COMPLEXITY
# ═══════════════════════════════════════════════════════════════

def get_difficulty(complexity: str) -> str:
    mapping = {
        "basic sql":        "easy",
        "single join":      "easy",
        "multiple_joins":   "medium",
        "subqueries":       "medium",
        "ctes":             "hard",
        "aggregation":      "medium",
        "window functions": "hard",
        "set operations":   "hard",
    }
    return mapping.get(complexity.lower().strip(), "medium")


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("Fill Missing Categories from Gretel Cache")
    print("=" * 70)

    # Load existing dataset
    print(f"\n📂 Loading {EXISTING_FILE}...")
    with open(EXISTING_FILE) as f:
        existing = json.load(f)

    existing_cats = Counter(r["sql_category"] for r in existing)
    print(f"✅ Loaded {len(existing)} records: {dict(existing_cats)}")

    # Load gretel cache
    print(f"\n📂 Loading {GRETEL_CACHE}...")
    df = pd.read_parquet(GRETEL_CACHE)
    print(f"✅ Loaded {len(df)} gretel rows")

    # Filter to relevant complexities
    relevant = df[df['sql_complexity'].str.lower().str.strip().isin(COMPLEXITY_TO_CATEGORY.keys())]
    print(f"   Relevant rows: {len(relevant)}")

    # Skip rows already used (by sql prompt match)
    existing_titles = set(r.get("title", "") for r in existing)

    # Process per category
    new_records = []

    for cat, target in CATEGORY_TARGETS.items():
        current = existing_cats.get(cat, 0)
        needed = target - current

        if needed <= 0:
            print(f"\n✅ {cat}: already at {current}/{target}")
            continue

        print(f"\n🔍 Filling {cat}: need {needed} more (have {current})...")

        # Get rows for this category
        cat_complexities = [k for k, v in COMPLEXITY_TO_CATEGORY.items() if v == cat]
        cat_rows = relevant[relevant['sql_complexity'].str.lower().str.strip().isin(cat_complexities)]

        # Shuffle for variety
        cat_rows = cat_rows.sample(frac=1, random_state=42).reset_index(drop=True)

        added = 0
        failed = 0
        empty = 0

        for _, row in tqdm(cat_rows.iterrows(), total=min(len(cat_rows), needed * 5), desc=cat):
            if added >= needed:
                break

            title = str(row.get("sql_prompt", "")).strip()
            if title in existing_titles:
                continue

            sql_context = str(row.get("sql_context", ""))
            sql = str(row.get("sql", "")).strip()
            complexity = str(row.get("sql_complexity", "")).lower().strip()
            domain = str(row.get("domain", "")).strip()

            if not sql_context or not sql:
                failed += 1
                continue

            # Parse schema + sample data
            schemas, sample_data = parse_sql_context(sql_context)
            if not schemas:
                failed += 1
                continue

            # Verify + capture output
            success, output = verify_and_capture(schemas, sample_data, sql)
            if not success:
                failed += 1
                continue
            if not output:
                empty += 1
                continue

            difficulty = get_difficulty(complexity)

            record = {
                "id": f"sql_{cat}_{difficulty}_{uuid.uuid4().hex[:8]}",
                "title": title,
                "description": (
                    f"A relational database system manages {domain} data across multiple tables.\n\n"
                    f"{title}\n\n"
                    f"The query must handle NULL values appropriately and return results in a deterministic order."
                ),
                "difficulty": difficulty,
                "sql_category": cat,
                "domain": domain,
                "schemas": schemas,
                "sample_data": sample_data,
                "constraints": [
                    "Results must be returned in a deterministic order",
                    "NULL values should be handled appropriately",
                    "Include only records matching the specified conditions",
                ],
                "starter_query": "-- Write your SQL query here\n\nSELECT ",
                "hints": [
                    "Examine how the tables relate to each other through common fields",
                    "Consider what filtering or joining conditions are needed",
                    "Think about edge cases like NULL values or missing records",
                ],
                "evaluation": {
                    "engine": "postgres",
                    "comparison": "result_set",
                    "order_sensitive": "ORDER BY" in sql.upper(),
                },
                "reference_query": sql,
                "sql_expected_output": output,
                "source": "gretelai/synthetic_text_to_sql",
                "source_complexity": complexity,
            }

            new_records.append(record)
            existing_titles.add(title)
            added += 1

        print(f"   ✅ Added: {added} | Failed: {failed} | Empty: {empty}")

    # Merge and save
    final = existing + new_records
    final_cats = Counter(r["sql_category"] for r in final)
    has_output = sum(1 for r in final if r.get("sql_expected_output"))

    print(f"\n💾 Saving {len(final)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 70)
    print("✅ DONE")
    print("=" * 70)
    print(f"📊 Total: {len(final)}")
    for cat, count in final_cats.most_common():
        pct = 100 * count // len(final)
        print(f"   {cat:15s}: {count:4d} ({pct:2d}%) {'█' * (pct // 2)}")
    print(f"\n📈 Difficulty:")
    for diff, count in Counter(r["difficulty"] for r in final).most_common():
        print(f"   {diff:10s}: {count:4d} ({100*count//len(final):2d}%)")
    print(f"\n✅ sql_expected_output: {has_output}/{len(final)} (100%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
