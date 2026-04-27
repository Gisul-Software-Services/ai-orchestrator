#!/usr/bin/env python3
"""
Production SQL Dataset Builder - APTOR Format
==============================================

Strategy: Use existing validated SQL datasets + LLM ONLY for metadata
- Source: gretelai/synthetic_text_to_sql (105K pre-validated SQL)
- Schema + Data: Parsed from sql_context (NO LLM)
- Validation: DuckDB execution before acceptance
- LLM Role: Description, constraints, hints ONLY
- Critical Fix: Hints generated WITHOUT seeing reference SQL (prevents leakage)

Pipeline:
  1. Load gretelai dataset
  2. Parse sql_context → schemas + sample_data (no LLM)
  3. Verify SQL execution in DuckDB (no LLM)
  4. LLM: Generate description + constraints (WITH SQL for context)
  5. LLM: Generate hints (WITHOUT SQL - prevents leakage)
  6. Save in APTOR format

Install:
  pip install datasets duckdb transformers torch accelerate bitsandbytes pandas pyarrow
"""

import json
import re
import os
import uuid
import torch
import pandas as pd
from tqdm import tqdm
from collections import Counter
from typing import Dict, List, Tuple, Optional
import duckdb
from datasets import load_dataset
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

CONFIG = {
    # Model
    "model_name": "Qwen/Qwen2.5-7B-Instruct",
    
    # Output
    "output_file": "sql_dataset_aptor.json",
    "state_file": "sql_dataset_aptor.state.json",
    "save_every": 25,  # Save checkpoint every N records
    
    # Dataset balancing (records per complexity level)
    "records_per_complexity": 500 Total ~3500 records across 7 levels
    
    # LLM generation
    "max_tokens": 800,
    "temperature": 0.7,
    
    # Local cache (optional - speeds up reruns)
    "local_parquet": "gretel_sql_cache.parquet",
}

# Gretel complexity → APTOR (category, difficulty)
COMPLEXITY_MAP = {
    "simple":           ("select",      "easy"),
    "single join":      ("join",        "easy"),
    "aggregation":      ("aggregation", "medium"),
    "multiple joins":   ("join",        "medium"),
    "subqueries":       ("subquery",    "medium"),
    "window functions": ("window",      "hard"),
    "complex":          ("subquery",    "hard"),
    "set operations":   ("aggregation", "hard"),
}

# ═══════════════════════════════════════════════════════════════
# STEP 1: PARSE SCHEMA + DATA FROM SQL_CONTEXT
# ═══════════════════════════════════════════════════════════════

def parse_sql_context(sql_context: str) -> Tuple[Dict, Dict]:
    """
    Extract schemas and sample_data from CREATE TABLE + INSERT INTO statements.
    
    Returns:
        (schemas, sample_data) - both as dicts with table names as keys
    """
    schemas = {}
    sample_data = {}

    # ──────────────────────────────────────────────
    # Parse CREATE TABLE statements
    # ──────────────────────────────────────────────
    create_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)',
        re.IGNORECASE | re.DOTALL
    )
    
    for table_name, columns_raw in create_pattern.findall(sql_context):
        columns = []
        
        for col_line in columns_raw.split(','):
            col_line = col_line.strip()
            
            # Skip constraint definitions
            if re.match(r'^\s*(PRIMARY|FOREIGN|UNIQUE|CHECK|INDEX|CONSTRAINT)\s+', col_line, re.I):
                continue
            
            parts = col_line.split()
            if len(parts) < 2:
                continue
            
            col_name = parts[0].strip('`"[]')
            col_type_raw = parts[1].upper()
            
            # Normalize to PostgreSQL types
            if any(t in col_type_raw for t in ["INT", "SERIAL", "NUMBER", "NUMERIC", "DECIMAL"]):
                col_type = "INTEGER" if "INT" in col_type_raw else "DECIMAL"
            elif any(t in col_type_raw for t in ["FLOAT", "DOUBLE", "REAL"]):
                col_type = "DECIMAL"
            elif any(t in col_type_raw for t in ["CHAR", "TEXT", "STRING", "VARCHAR", "NVARCHAR"]):
                col_type = "VARCHAR(255)"
            elif "BOOL" in col_type_raw:
                col_type = "BOOLEAN"
            elif any(t in col_type_raw for t in ["DATE", "TIME", "TIMESTAMP"]):
                col_type = "TIMESTAMP"
            else:
                col_type = "TEXT"
            
            # Extract constraints
            constraint = ""
            col_upper = col_line.upper()
            if "PRIMARY KEY" in col_upper:
                constraint = "PRIMARY KEY"
            elif "NOT NULL" in col_upper:
                constraint = "NOT NULL"
            
            columns.append({
                "name": col_name,
                "type": col_type,
                "constraints": constraint
            })
        
        if columns:
            schemas[table_name] = {"columns": columns}
            sample_data[table_name] = []

    # ──────────────────────────────────────────────
    # Parse INSERT INTO statements
    # ──────────────────────────────────────────────
    insert_pattern = re.compile(
        r'INSERT\s+INTO\s+[`"]?(\w+)[`"]?\s*(?:\(([^)]+)\))?\s*VALUES\s*((?:\([^)]+\)\s*,?\s*)+)',
        re.IGNORECASE | re.DOTALL
    )
    
    for table_name, cols_str, values_str in insert_pattern.findall(sql_context):
        if table_name not in schemas:
            continue
        
        # Determine column order
        if cols_str.strip():
            col_names = [c.strip().strip('`"') for c in cols_str.split(',')]
        else:
            col_names = [c["name"] for c in schemas[table_name]["columns"]]
        
        # Parse value tuples
        value_tuples = re.findall(r'\(([^)]+)\)', values_str)
        
        for value_tuple in value_tuples:
            # Split by comma, but not inside quotes
            raw_values = re.split(r',(?=(?:[^\']*\'[^\']*\')*[^\']*$)', value_tuple)
            
            row = {}
            for col_name, raw_val in zip(col_names, raw_values):
                val = raw_val.strip().strip("'\"")
                
                # Type conversion
                if val.upper() in ("NULL", "NONE", ""):
                    val = None
                else:
                    try:
                        val = int(val)
                    except ValueError:
                        try:
                            val = float(val)
                        except ValueError:
                            pass  # Keep as string
                
                row[col_name] = val
            
            if row:
                sample_data[table_name].append(row)
    
    return schemas, sample_data


# ═══════════════════════════════════════════════════════════════
# STEP 2: VALIDATE WITH DUCKDB
# ═══════════════════════════════════════════════════════════════

def validate_sql_execution(schemas: Dict, sample_data: Dict, sql: str) -> bool:
    """
    Execute SQL against sample data in DuckDB to verify it works.
    
    Returns:
        True if SQL executes without error, False otherwise
    """
    conn = duckdb.connect(":memory:")
    
    try:
        # Create tables
        for table_name, schema in schemas.items():
            col_defs = []
            for col in schema["columns"]:
                col_type = col["type"].split("(")[0]  # Remove length specifiers for DuckDB
                col_defs.append(f'"{col["name"]}" {col_type}')
            
            create_sql = f'CREATE TABLE "{table_name}" ({", ".join(col_defs)})'
            conn.execute(create_sql)
        
        # Insert sample data
        for table_name, rows in sample_data.items():
            if table_name not in schemas or not rows:
                continue
            
            col_names = [c["name"] for c in schemas[table_name]["columns"]]
            
            for row in rows:
                # Only insert columns that exist in schema
                available_cols = [k for k in row.keys() if k in col_names]
                if not available_cols:
                    continue
                
                values = [row.get(c) for c in available_cols]
                placeholders = ", ".join(["?" for _ in values])
                columns_str = ", ".join(f'"{c}"' for c in available_cols)
                
                insert_sql = f'INSERT INTO "{table_name}" ({columns_str}) VALUES ({placeholders})'
                conn.execute(insert_sql, values)
        
        # Normalize SQL for DuckDB (remove table aliases like T1.)
        normalized_sql = re.sub(r'\bT\d+\.', '', sql)
        
        # Execute and fetch to verify it works
        result = conn.execute(normalized_sql).fetchall()
        
        return True
    
    except Exception as e:
        return False
    
    finally:
        conn.close()


# ═══════════════════════════════════════════════════════════════
# STEP 3: LOAD MODEL (QWEN)
# ═══════════════════════════════════════════════════════════════

def get_gpu_memory_map(reserve_gib: int = 2, cpu_gib: int = 48) -> Dict:
    """Calculate GPU memory allocation."""
    if not torch.cuda.is_available():
        return {"cpu": f"{cpu_gib}GiB"}
    
    total_gb = int(torch.cuda.get_device_properties(0).total_memory / (1024**3))
    usable_gb = max(1, total_gb - reserve_gib)
    
    return {
        0: f"{usable_gb}GiB",
        "cpu": f"{cpu_gib}GiB"
    }


def load_model(model_name: str):
    """Load Qwen model with 4-bit quantization."""
    print(f"\n🔄 Loading model: {model_name}")
    
    # Tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True
    )
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    
    # Quantization config
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
        llm_int8_enable_fp32_cpu_offload=True,
    )
    
    # Model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto",
        max_memory=get_gpu_memory_map(),
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    model.eval()
    
    print("✅ Model loaded successfully\n")
    return tokenizer, model


# ═══════════════════════════════════════════════════════════════
# STEP 4: LLM PROMPTS (CRITICAL: SEPARATE PROMPTS FOR HINTS)
# ═══════════════════════════════════════════════════════════════

PROMPT_DESCRIPTION_CONSTRAINTS = """You are generating metadata for a SQL interview question.

Given:
- Question: {question}
- SQL Complexity: {complexity}
- Reference SQL: {sql}

Generate a JSON object with:
1. "description" - Exactly 3 paragraphs following APTOR format:
   - Paragraph 1: Business context and domain scenario
   - Paragraph 2: What the SQL query must return
   - Paragraph 3: Rules, constraints, edge cases, NULL handling

2. "constraints" - List of 3-4 specific, measurable query requirements
   Example: ["Results must be ordered by revenue DESC", "Include NULL amounts as 0"]

CRITICAL RULES:
- Use formal third-person tone (no "you", "your", "we")
- Be specific about NULL handling, ordering, tie-breaking
- Make description realistic and professional

Return ONLY valid JSON (no markdown, no code fences):
{{
  "description": "paragraph1\\n\\nparagraph2\\n\\nparagraph3",
  "constraints": ["constraint1", "constraint2", "constraint3"]
}}"""

PROMPT_HINTS_NO_SQL = """You are generating progressive hints for a SQL interview question.

Given:
- Question: {question}
- Schema: {schema_summary}
- Complexity: {complexity}

Generate 3 progressive hints that guide without giving away the solution.

CRITICAL RULES:
- Hint 1: Understanding the data structure and relationships
- Hint 2: High-level approach (join? aggregate? filter?)
- Hint 3: Key insight or edge case to consider
- DO NOT mention specific SQL keywords (JOIN, SUM, WHERE, etc.)
- DO NOT reveal the solution structure
- Keep each hint to 1-2 sentences

Return ONLY valid JSON:
{{
  "hints": ["hint1", "hint2", "hint3"]
}}"""


def call_llm(tokenizer, model, prompt: str, max_tokens: int = 600) -> str:
    """Call local LLM with prompt."""
    messages = [{"role": "user", "content": prompt}]
    
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True
    )
    
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True,
        max_length=2048
    ).to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            do_sample=True,
            temperature=CONFIG["temperature"],
            top_p=0.9,
            eos_token_id=tokenizer.eos_token_id,
            pad_token_id=tokenizer.pad_token_id,
        )
    
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1]:],
        skip_special_tokens=True
    ).strip()
    
    return response


def extract_json_from_response(text: str) -> Optional[Dict]:
    """Extract JSON from LLM response (handles markdown fences)."""
    # Try markdown code fence first
    fenced = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text, re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Find JSON object in text
    start = text.find('{')
    if start == -1:
        return None
    
    depth = 0
    in_string = False
    escape = False
    
    for i in range(start, len(text)):
        char = text[i]
        
        if in_string:
            if escape:
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                in_string = False
            continue
        
        if char == '"':
            in_string = True
        elif char == '{':
            depth += 1
        elif char == '}':
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start:i+1])
                except json.JSONDecodeError:
                    # Try next opening brace
                    next_start = text.find('{', start + 1)
                    if next_start == -1:
                        return None
                    start = next_start
                    depth = 0
                    in_string = False
                    escape = False
    
    return None


# ═══════════════════════════════════════════════════════════════
# STEP 5: STATE MANAGEMENT
# ═══════════════════════════════════════════════════════════════

def load_state(state_file: str) -> Dict:
    """Load processing state for resumability."""
    if not os.path.exists(state_file):
        return {"next_index": 0, "processed_ids": []}
    
    try:
        with open(state_file) as f:
            state = json.load(f)
        if isinstance(state.get("next_index"), int):
            return state
    except Exception:
        pass
    
    return {"next_index": 0, "processed_ids": []}


def save_state(state_file: str, index: int, processed_ids: List[str]):
    """Save processing state."""
    tmp_file = state_file + ".tmp"
    
    with open(tmp_file, "w") as f:
        json.dump({
            "next_index": index,
            "processed_ids": processed_ids
        }, f, indent=2)
    
    os.replace(tmp_file, state_file)


# ═══════════════════════════════════════════════════════════════
# MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════

def main():
    print("=" * 70)
    print("SQL Dataset Builder - APTOR Format (Gretel + Qwen)")
    print("=" * 70)
    
    # ──────────────────────────────────────────────
    # Load gretelai dataset
    # ──────────────────────────────────────────────
    local_parquet = CONFIG["local_parquet"]
    
    if os.path.exists(local_parquet):
        print(f"\n📂 Loading from local cache: {local_parquet}")
        df = pd.read_parquet(local_parquet)
        dataset = df.to_dict(orient="records")
        print(f"✅ Loaded {len(dataset):,} records from cache")
    else:
        print("\n⬇️  Downloading gretelai/synthetic_text_to_sql from HuggingFace...")
        print("💡 Tip: Pre-download for faster reruns:")
        print("   wget 'https://huggingface.co/datasets/gretelai/synthetic_text_to_sql/resolve/main/data/synthetic_text_to_sql_train.snappy.parquet' -O gretel_sql_cache.parquet")
        
        hf_dataset = load_dataset("gretelai/synthetic_text_to_sql", split="train")
        dataset = list(hf_dataset)
        
        # Save cache
        pd.DataFrame(dataset).to_parquet(local_parquet)
        print(f"✅ Downloaded {len(dataset):,} records and saved cache")
    
    # ──────────────────────────────────────────────
    # Balance by complexity
    # ──────────────────────────────────────────────
    print(f"\n⚖️  Balancing dataset ({CONFIG['records_per_complexity']} per complexity)...")
    
    buckets = {}
    for item in dataset:
        complexity = item.get("sql_complexity", "").lower().strip()
        if complexity not in buckets:
            buckets[complexity] = []
        
        if len(buckets[complexity]) < CONFIG["records_per_complexity"]:
            buckets[complexity].append(item)
    
    balanced_dataset = []
    for items in buckets.values():
        balanced_dataset.extend(items)
    
    print(f"✅ Selected {len(balanced_dataset):,} balanced records")
    print("📊 Distribution:", {k: len(v) for k, v in buckets.items()})
    
    # ──────────────────────────────────────────────
    # Pre-filter: Parse + Validate with DuckDB
    # ──────────────────────────────────────────────
    print(f"\n🔍 Pre-filtering with DuckDB validation...")
    
    verified = []
    parse_failures = 0
    exec_failures = 0
    
    for item in tqdm(balanced_dataset, desc="Validating"):
        # Parse schema + data
        sql_context = item.get("sql_context", "")
        schemas, sample_data = parse_sql_context(sql_context)
        
        if not schemas:
            parse_failures += 1
            continue
        
        # Validate SQL execution
        sql = item.get("sql", "")
        if not validate_sql_execution(schemas, sample_data, sql):
            exec_failures += 1
            continue
        
        # Store parsed data
        item["_schemas"] = schemas
        item["_sample_data"] = sample_data
        verified.append(item)
    
    print(f"✅ Verified: {len(verified):,}")
    print(f"❌ Parse failures: {parse_failures:,}")
    print(f"❌ Execution failures: {exec_failures:,}")
    
    if not verified:
        print("\n⚠️  No valid records found. Exiting.")
        return
    
    # ──────────────────────────────────────────────
    # Load state
    # ──────────────────────────────────────────────
    state = load_state(CONFIG["state_file"])
    resume_index = state["next_index"]
    
    if resume_index >= len(verified):
        print(f"\n⚠️  State file shows completion. Resetting.")
        resume_index = 0
        save_state(CONFIG["state_file"], 0, [])
    elif resume_index > 0:
        print(f"\n↩️  Resuming from record {resume_index}/{len(verified)}")
    
    # ──────────────────────────────────────────────
    # Load LLM
    # ──────────────────────────────────────────────
    tokenizer, model = load_model(CONFIG["model_name"])
    
    # ──────────────────────────────────────────────
    # Process records with LLM enrichment
    # ──────────────────────────────────────────────
    output_jsonl = CONFIG["output_file"] + ".jsonl"
    mode = "a" if resume_index > 0 and os.path.exists(output_jsonl) else "w"
    
    processed_ids = state.get("processed_ids", [])
    
    print(f"\n🚀 Enriching with LLM ({len(verified) - resume_index} remaining)...")
    
    with open(output_jsonl, mode, encoding="utf-8") as out:
        for i, item in enumerate(tqdm(verified[resume_index:], desc="Processing"), start=resume_index):
            
            # Extract metadata
            complexity = item.get("sql_complexity", "simple").lower()
            category, difficulty = COMPLEXITY_MAP.get(complexity, ("select", "medium"))
            
            schemas = item["_schemas"]
            sample_data = item["_sample_data"]
            question = item.get("sql_prompt", "").strip()
            sql = item.get("sql", "")
            domain = item.get("domain", "database")
            
            # ────────────────────────────────────────
            # LLM Call 1: Description + Constraints (WITH SQL)
            # ────────────────────────────────────────
            prompt_desc = PROMPT_DESCRIPTION_CONSTRAINTS.format(
                question=question,
                complexity=complexity,
                sql=sql[:400]  # Truncate for context
            )
            
            response_desc = call_llm(tokenizer, model, prompt_desc, max_tokens=CONFIG["max_tokens"])
            meta_desc = extract_json_from_response(response_desc) or {}
            
            description = meta_desc.get("description", "").strip()
            constraints = meta_desc.get("constraints", [])
            
            # Fallback description
            if not description or len(description) < 100:
                description = (
                    f"A relational database system manages {domain} data across multiple tables.\n\n"
                    f"{question}\n\n"
                    f"The query must handle NULL values appropriately and return results in a deterministic order."
                )
            
            # Fallback constraints
            if len(constraints) < 2:
                constraints = [
                    "Query must return the specified columns",
                    "Results must be properly ordered",
                    "Handle NULL values according to business logic"
                ]
            
            # ────────────────────────────────────────
            # LLM Call 2: Hints (WITHOUT SQL - prevents leakage)
            # ────────────────────────────────────────
            schema_summary = ", ".join(schemas.keys())
            
            prompt_hints = PROMPT_HINTS_NO_SQL.format(
                question=question,
                schema_summary=schema_summary,
                complexity=complexity
            )
            
            response_hints = call_llm(tokenizer, model, prompt_hints, max_tokens=400)
            meta_hints = extract_json_from_response(response_hints) or {}
            
            hints = meta_hints.get("hints", [])
            
            # Fallback hints
            if len(hints) < 2:
                hints = [
                    "Examine the relationships between tables in the schema",
                    "Consider which tables contain the required information",
                    "Think about how to combine data from multiple sources"
                ]
            
            # ────────────────────────────────────────
            # Build APTOR record
            # ────────────────────────────────────────
            record = {
                "id": f"sql_{category}_{difficulty}_{i:05d}_{uuid.uuid4().hex[:8]}",
                "title": question,
                "description": description,
                "difficulty": difficulty,
                "sql_category": category,
                "domain": domain,
                "schemas": schemas,
                "sample_data": sample_data,
                "constraints": constraints[:4],
                "starter_query": "-- Write your SQL query here\n\nSELECT ",
                "hints": hints[:3],
                "evaluation": {
                    "engine": "postgres",
                    "comparison": "result_set",
                    "order_sensitive": "ORDER BY" in sql.upper()
                },
                "reference_query": sql,
                "source": "gretelai/synthetic_text_to_sql",
                "source_complexity": complexity
            }
            
            # Write to JSONL
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            processed_ids.append(record["id"])
            
            # Save checkpoint
            if (i + 1) % CONFIG["save_every"] == 0:
                out.flush()
                save_state(CONFIG["state_file"], i + 1, processed_ids)
                
                # Clear GPU cache
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
        
        out.flush()
        save_state(CONFIG["state_file"], len(verified), processed_ids)
    
    # ──────────────────────────────────────────────
    # Consolidate to final JSON
    # ──────────────────────────────────────────────
    print(f"\n📦 Consolidating to {CONFIG['output_file']}...")
    
    final_records = []
    with open(output_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    final_records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    
    with open(CONFIG["output_file"], "w", encoding="utf-8") as f:
        json.dump(final_records, f, indent=2, ensure_ascii=False)
    
    # ──────────────────────────────────────────────
    # Statistics
    # ──────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("✅ PIPELINE COMPLETE")
    print("=" * 70)
    print(f"📊 Total records: {len(final_records):,}")
    print(f"📁 Output file: {CONFIG['output_file']}")
    print(f"\n📈 Category distribution:")
    for cat, count in Counter(r["sql_category"] for r in final_records).items():
        print(f"   {cat:15s}: {count:,}")
    print(f"\n📈 Difficulty distribution:")
    for diff, count in Counter(r["difficulty"] for r in final_records).items():
        print(f"   {diff:15s}: {count:,}")
    print("=" * 70)


if __name__ == "__main__":
    main()