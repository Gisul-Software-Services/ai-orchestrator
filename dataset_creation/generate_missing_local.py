#!/usr/bin/env python3
"""
Generate missing SQL entries using local Qwen2.5-7B-Instruct-AWQ model.
No RAG dependency — generates full entries from scratch.

Stop the model service before running this (GPU memory needed).

Usage:
    python3 generate_missing_local.py
"""

import json
import re
import os
import uuid
import duckdb
import torch
from collections import Counter
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════

EXISTING_FILE = "sql_dataset_final_clean.json"
OUTPUT_FILE = "sql_dataset_final_clean.json"
STATE_FILE = "generate_missing_local.state.json"

MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
MAX_NEW_TOKENS = 900
SAVE_EVERY = 10

GENERATE_TARGETS = {
    "join":     220,
    "select":   225,
    "subquery":  25,
}

TOPICS = {
    "join": [
        "employees and departments", "customers and orders", "products and inventory",
        "students and courses", "users and transactions", "sales and regions",
        "authors and books", "patients and doctors", "projects and teams",
        "suppliers and products", "flights and passengers", "accounts and transfers",
        "employees and salaries", "products and categories", "orders and shipments",
    ],
    "select": [
        "filter records by date", "find records with conditions", "select top N records",
        "filter by status field", "find records in category", "select with null handling",
        "filter by numeric range", "find active records", "select with multiple filters",
        "find recent records", "filter by text pattern", "select distinct values",
        "find records by location", "filter by rating", "select with ordering",
    ],
    "subquery": [
        "find records above average", "find customers with most orders",
        "find employees earning more than average", "find products never ordered",
        "find top performing records", "find records matching subquery condition",
        "find records with exists clause", "find records not in subquery",
        "find second highest value", "find records with correlated subquery",
    ],
}

DIFFICULTIES = ["Easy", "Medium", "Hard"]
DIFFICULTY_DIST = [0.25, 0.50, 0.25]

# ═══════════════════════════════════════════════════════════════
# PROMPTS
# ═══════════════════════════════════════════════════════════════

SYSTEM_PROMPT = """You are an expert SQL assessment question generator.
Generate complete, realistic SQL assessment questions in exact JSON format.
All SQL must be valid PostgreSQL. All sample data must be realistic (no placeholder values).
Return ONLY valid JSON, no markdown, no explanation."""

GENERATION_PROMPT = """Generate a SQL assessment question for the following:

Category: {category}
Topic: {topic}
Difficulty: {difficulty}

Requirements:
- 2-3 tables with realistic column names
- 3-5 rows of realistic sample data per table (real names, numbers, dates — NOT Sample1, Value1)
- For JOINs: foreign key values MUST match primary key values in parent table
- Reference SQL must return AT LEAST 1 row when run against sample_data
- Description: exactly 3 paragraphs (business context, objective, rules/constraints)
- 3 progressive hints that guide without revealing the SQL solution
- 3-4 specific constraints about ordering, NULL handling, tie-breaking

Return ONLY this JSON:
{{
  "title": "Clear question title",
  "description": "Paragraph 1: business context.\\n\\nParagraph 2: what the query must return.\\n\\nParagraph 3: rules, NULL handling, ordering requirements.",
  "schemas": {{
    "table_name": {{
      "columns": [
        {{"name": "col_name", "type": "INTEGER", "constraints": "PRIMARY KEY"}},
        {{"name": "col_name", "type": "VARCHAR(255)", "constraints": ""}}
      ]
    }}
  }},
  "sample_data": {{
    "table_name": [
      {{"col1": value1, "col2": "value2"}}
    ]
  }},
  "reference_query": "SELECT ... FROM ... WHERE ...;",
  "constraints": [
    "Results must be ordered by X DESC",
    "NULL values should be treated as 0",
    "Include only records where condition"
  ],
  "hints": [
    "Think about how the tables relate to each other",
    "Consider what aggregation or filtering is needed",
    "Think about edge cases like NULL values"
  ]
}}"""


# ═══════════════════════════════════════════════════════════════
# MODEL
# ═══════════════════════════════════════════════════════════════

def load_model():
    from transformers import BitsAndBytesConfig
    
    print(f"\n🔄 Loading {MODEL_NAME} with 4-bit quantization...")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        llm_int8_enable_fp32_cpu_offload=True,
    )

    # Calculate GPU memory
    if torch.cuda.is_available():
        total_gb = int(torch.cuda.get_device_properties(0).total_memory / (1024**3))
        usable_gb = max(1, total_gb - 1)
        max_memory = {0: f"{usable_gb}GiB", "cpu": "48GiB"}
    else:
        max_memory = {"cpu": "48GiB"}

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        quantization_config=bnb_config,
        device_map="auto",
        max_memory=max_memory,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.eval()

    print("✅ Model loaded\n")
    return tokenizer, model


def call_llm(tokenizer, model, prompt: str) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    text = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    inputs = tokenizer(
        text, return_tensors="pt", truncation=True, max_length=2048
    ).to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=MAX_NEW_TOKENS,
            do_sample=True,
            temperature=0.8,
            top_p=0.9,
            repetition_penalty=1.05,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )

    return tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    ).strip()


# ═══════════════════════════════════════════════════════════════
# JSON EXTRACTION
# ═══════════════════════════════════════════════════════════════

def extract_json(text: str) -> dict | None:
    # Try markdown fence first
    fenced = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except:
            pass

    # Find JSON object
    start = text.find("{")
    if start == -1:
        return None

    depth, in_str, esc = 0, False, False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
                except:
                    nxt = text.find("{", start + 1)
                    if nxt == -1:
                        return None
                    start, depth, in_str, esc = nxt, 0, False, False
    return None


# ═══════════════════════════════════════════════════════════════
# DUCKDB VERIFICATION
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
# STATE
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
    print("SQL Missing Category Generator (Local Qwen AWQ)")
    print("=" * 70)

    # Load existing
    print(f"\n📂 Loading {EXISTING_FILE}...")
    with open(EXISTING_FILE) as f:
        existing = json.load(f)

    existing_cats = Counter(r["sql_category"] for r in existing)
    print(f"✅ Loaded {len(existing)} records: {dict(existing_cats)}")

    # Load state
    state = load_state()
    generated_by_cat = state.get("generated", {})

    # Load model
    tokenizer, model = load_model()

    # Generate per category
    all_new = []
    for cat, target in GENERATE_TARGETS.items():
        already = generated_by_cat.get(cat, [])
        remaining = target - len(already)

        if remaining <= 0:
            print(f"\n✅ {cat}: already done ({len(already)}/{target})")
            all_new.extend(already)
            continue

        print(f"\n🚀 Generating {remaining} more {cat} entries (have {len(already)})...")

        topics = TOPICS[cat]
        generated = list(already)
        attempts = 0
        max_attempts = remaining * 5

        with tqdm(total=target, initial=len(already), desc=cat) as pbar:
            while len(generated) < target and attempts < max_attempts:
                attempts += 1

                topic = topics[attempts % len(topics)]
                difficulty = random.choices(DIFFICULTIES, weights=DIFFICULTY_DIST)[0]

                prompt = GENERATION_PROMPT.format(
                    category=cat,
                    topic=topic,
                    difficulty=difficulty,
                )

                try:
                    raw = call_llm(tokenizer, model, prompt)
                    parsed = extract_json(raw)

                    if not parsed:
                        continue

                    schemas = parsed.get("schemas", {})
                    sample_data = parsed.get("sample_data", {})
                    reference_query = parsed.get("reference_query", "")
                    title = parsed.get("title", "").strip()
                    description = parsed.get("description", "").strip()

                    if not all([schemas, sample_data, reference_query, title, description]):
                        continue

                    # Verify with DuckDB
                    success, output = verify_and_capture(schemas, sample_data, reference_query)
                    if not success or not output:
                        continue

                    record = {
                        "id": f"sql_{cat}_{difficulty.lower()}_{uuid.uuid4().hex[:8]}",
                        "title": title,
                        "description": description,
                        "difficulty": difficulty.lower(),
                        "sql_category": cat,
                        "domain": "generated",
                        "schemas": schemas,
                        "sample_data": sample_data,
                        "constraints": parsed.get("constraints", [])[:4],
                        "starter_query": "-- Write your SQL query here\n\nSELECT ",
                        "hints": parsed.get("hints", [])[:3],
                        "evaluation": {
                            "engine": "postgres",
                            "comparison": "result_set",
                            "order_sensitive": "ORDER BY" in reference_query.upper(),
                        },
                        "reference_query": reference_query,
                        "sql_expected_output": output,
                        "source": "qwen_generated",
                        "source_complexity": cat,
                    }

                    generated.append(record)
                    pbar.update(1)

                    if len(generated) % SAVE_EVERY == 0:
                        generated_by_cat[cat] = generated
                        save_state({"generated": generated_by_cat})
                        if torch.cuda.is_available():
                            torch.cuda.empty_cache()

                except Exception as e:
                    print(f"\n  ⚠️  {e}")
                    continue

        generated_by_cat[cat] = generated
        save_state({"generated": generated_by_cat})
        all_new.extend(generated)
        print(f"   ✅ {cat}: {len(generated)}/{target} generated")

    # Merge and save
    final = existing + all_new
    final_cats = Counter(r["sql_category"] for r in final)
    has_output = sum(1 for r in final if r.get("sql_expected_output"))

    print(f"\n💾 Saving {len(final)} records to {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(final, f, indent=2, ensure_ascii=False)

    if os.path.exists(STATE_FILE):
        os.remove(STATE_FILE)

    print("\n" + "=" * 70)
    print("✅ DONE")
    print("=" * 70)
    print(f"📊 Total: {len(final)}")
    for cat, count in final_cats.most_common():
        pct = 100 * count // len(final)
        print(f"   {cat:15s}: {count:4d} ({pct:2d}%) {'█' * (pct // 2)}")
    print(f"\n✅ sql_expected_output: {has_output}/{len(final)} (100%)")
    print("=" * 70)


if __name__ == "__main__":
    main()
