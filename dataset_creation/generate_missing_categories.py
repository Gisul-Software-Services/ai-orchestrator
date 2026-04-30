#!/usr/bin/env python3
"""
Generate missing SQL entries for short categories (join, select, subquery)
by calling the running Qwen model service at http://127.0.0.1:7001.

Generates full APTOR-format entries with DuckDB verification.

Usage:
    # Start model service first, then:
    python3 generate_missing_categories.py
"""

import json
import re
import os
import uuid
import duckdb
import urllib.request
import urllib.error
from collections import Counter
from tqdm import tqdm

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

EXISTING_FILE = "sql_dataset_final_clean.json"
OUTPUT_FILE = "sql_dataset_final_clean.json"  # overwrite with merged result
STATE_FILE = "generate_missing.state.json"
MODEL_URL = "http://127.0.0.1:7001/api/v1/generate-sql-question"

# How many to generate per category
GENERATE_TARGETS = {
    "join": 220,       # have 89, need 300+
    "select": 225,     # have 81, need 300+
    "subquery": 25,    # have 280, need 300+
}

SAVE_EVERY = 10

# Topics per category for variety
TOPICS = {
    "join": [
        "employee department join", "customer orders join", "product inventory join",
        "student course enrollment join", "user activity join", "sales region join",
        "author book publisher join", "patient doctor hospital join",
        "project team member join", "supplier product join",
        "transaction account join", "flight passenger join",
    ],
    "select": [
        "filter by date range", "select with conditions", "filter by status",
        "select top records", "filter by category", "select with multiple conditions",
        "filter by price range", "select active users", "filter by location",
        "select recent records", "filter by rating", "select with null handling",
    ],
    "subquery": [
        "subquery with exists", "correlated subquery", "subquery in where clause",
        "subquery with in operator", "subquery for max value", "nested subquery",
        "subquery with aggregation", "subquery for ranking", "subquery with not exists",
        "subquery in select clause",
    ],
}

DIFFICULTIES = ["Easy", "Medium", "Hard"]
DIFFICULTY_WEIGHTS = [0.25, 0.50, 0.25]  # 25% easy, 50% medium, 25% hard

# ═══════════════════════════════════════════════════════════════
# CALL MODEL SERVICE
# ═══════════════════════════════════════════════════════════════

def call_model_service(topic: str, difficulty: str, sql_category: str) -> dict | None:
    """Call the running model service to generate a SQL question."""
    payload = json.dumps({
        "difficulty": difficulty,
        "topic": topic,
        "sql_category": sql_category,
        "count": 1,
    }).encode()

    req = urllib.request.Request(
        MODEL_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"\n  HTTP {e.code}: {e.read().decode()[:100]}")
        return None
    except Exception as e:
        print(f"\n  Error: {e}")
        return None


# ═══════════════════════════════════════════════════════════════
# DUCKDB VERIFICATION
# ═══════════════════════════════════════════════════════════════

def verify_and_capture(schemas: dict, sample_data: dict, sql: str) -> tuple:
    """Execute SQL in DuckDB and capture result rows."""
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

        result = conn.execute(sql).fetchall()
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
# STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def load_state() -> dict:
    if not os.path.exists(STATE_FILE):
        return {"generated": {}}
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except:
        return {"generated": {}}


def save_state(state: dict):
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    import random

    print("=" * 70)
    print("SQL Missing Category Generator")
    print("=" * 70)

    # Load existing dataset
    print(f"\n📂 Loading {EXISTING_FILE}...")
    with open(EXISTING_FILE) as f:
        existing = json.load(f)

    existing_cats = Counter(r["sql_category"] for r in existing)
    print(f"✅ Loaded {len(existing)} existing records")
    print(f"   Current distribution: {dict(existing_cats)}")

    # Load state
    state = load_state()
    generated_by_cat = state.get("generated", {cat: [] for cat in GENERATE_TARGETS})

    # Check model service is up
    print("\n🔌 Checking model service...")
    try:
        test = call_model_service("joins", "Easy", "join")
        if test:
            print("✅ Model service is running")
        else:
            print("❌ Model service returned no result — check it's running")
            return
    except Exception as e:
        print(f"❌ Cannot reach model service: {e}")
        print("   Start it first: cd /root/gisul_model && python3 -m backend.model_app.main")
        return

    # Generate for each short category
    new_records = []
    for cat, target in GENERATE_TARGETS.items():
        already = len(generated_by_cat.get(cat, []))
        remaining = target - already
        if remaining <= 0:
            print(f"\n✅ {cat}: already have {already}/{target}")
            new_records.extend(generated_by_cat[cat])
            continue

        print(f"\n🚀 Generating {remaining} {cat} entries...")

        topics = TOPICS[cat]
        generated = list(generated_by_cat.get(cat, []))
        attempts = 0
        max_attempts = remaining * 4  # allow 4x attempts for failures

        with tqdm(total=remaining, desc=cat) as pbar:
            while len(generated) < target and attempts < max_attempts:
                attempts += 1

                # Pick topic and difficulty
                topic = topics[attempts % len(topics)]
                difficulty = random.choices(DIFFICULTIES, weights=DIFFICULTY_WEIGHTS)[0]

                # Call model service
                result = call_model_service(topic, difficulty, cat)
                if not result:
                    continue

                # Validate required fields
                schemas = result.get("schemas", {})
                sample_data = result.get("sample_data", {})
                reference_query = result.get("reference_query", "")

                if not schemas or not sample_data or not reference_query:
                    continue

                # Verify with DuckDB + capture expected output
                success, output = verify_and_capture(schemas, sample_data, reference_query)
                if not success or not output:
                    continue

                # Build APTOR record
                record = {
                    "id": f"sql_{cat}_{difficulty.lower()}_{uuid.uuid4().hex[:8]}",
                    "title": result.get("title", ""),
                    "description": result.get("description", ""),
                    "difficulty": result.get("difficulty", difficulty.lower()),
                    "sql_category": cat,
                    "domain": "generated",
                    "schemas": schemas,
                    "sample_data": sample_data,
                    "constraints": result.get("constraints", []),
                    "starter_query": result.get("starter_query", "-- Write your SQL query here\n\nSELECT "),
                    "hints": result.get("hints", []),
                    "evaluation": result.get("evaluation", {
                        "engine": "postgres",
                        "comparison": "result_set",
                        "order_sensitive": False,
                    }),
                    "reference_query": reference_query,
                    "sql_expected_output": output,
                    "source": "qwen_generated",
                    "source_complexity": cat,
                }

                generated.append(record)
                pbar.update(1)

                # Save checkpoint
                if len(generated) % SAVE_EVERY == 0:
                    generated_by_cat[cat] = generated
                    save_state({"generated": generated_by_cat})

        generated_by_cat[cat] = generated
        save_state({"generated": generated_by_cat})
        new_records.extend(generated)
        print(f"   ✅ Generated {len(generated)}/{target} for {cat}")

    # Merge with existing
    print(f"\n🔀 Merging {len(new_records)} new records with {len(existing)} existing...")
    final = existing + new_records

    # Final stats
    final_cats = Counter(r["sql_category"] for r in final)
    final_diffs = Counter(r["difficulty"] for r in final)
    has_output = sum(1 for r in final if r.get("sql_expected_output"))

    # Save
    print(f"\n💾 Saving {len(final)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("\n" + "=" * 70)
    print("✅ DONE")
    print("=" * 70)
    print(f"📊 Total records: {len(final)}")
    print(f"\n📈 Category distribution:")
    for cat, count in final_cats.most_common():
        pct = 100 * count // len(final)
        bar = "█" * (pct // 2)
        print(f"   {cat:15s}: {count:4d} ({pct:2d}%) {bar}")
    print(f"\n📈 Difficulty distribution:")
    for diff, count in final_diffs.most_common():
        print(f"   {diff:10s}: {count:4d} ({100*count//len(final):2d}%)")
    print(f"\n✅ sql_expected_output: {has_output}/{len(final)} ({100*has_output//len(final)}%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
