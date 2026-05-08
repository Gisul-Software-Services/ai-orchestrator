#!/usr/bin/env python3
"""
Step 2: Build SQL Schemas Library from open-source datasets.

Sources:
  1. Spider tables.json  -> extract real multi-table schemas
  2. gretelai_extended.parquet -> extract unique schemas from sql_context
  3. Hand-crafted schemas -> classic DBs (Chinook, Northwind, Sakila style)
     + recursive/CTE/pivot schemas

Output:
  sql_schemas_library.json  - 700+ schemas in your MongoDB format

Usage:
  python build_sql_schemas_library.py

NOTE: OFFLINE only. Does NOT touch any running service.
"""

import json
import re
import hashlib
from pathlib import Path
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).parent
SPIDER_DIR = BASE_DIR / "spider_raw"
GRETELAI_CACHE = BASE_DIR / "gretelai_extended.parquet"
OUTPUT_FILE = BASE_DIR / "sql_schemas_library.json"

# ─────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────

def schema_signature(tables: dict) -> str:
    parts = []
    for tname in sorted(tables.keys()):
        cols = tables[tname].get("columns", [])
        col_sig = "_".join(sorted(f"{c['name']}:{c['type']}" for c in cols))
        parts.append(f"{tname}:{col_sig}")
    return hashlib.md5("|".join(parts).encode()).hexdigest()[:12]


def detect_relationships(tables: dict) -> List[dict]:
    rels = []
    for tname, tdef in tables.items():
        for col in tdef.get("columns", []):
            cname = col.get("name", "")
            if cname.endswith("_id") and cname != "id":
                ref = cname[:-3]
                for other in tables:
                    if other.lower() in (ref.lower(), ref.lower() + "s"):
                        rels.append({
                            "from_table": tname,
                            "from_column": cname,
                            "to_table": other,
                            "to_column": "id",
                            "relationship_type": "many-to-one"
                        })
                        break
    return rels


def calc_metadata(tables: dict) -> dict:
    table_count = len(tables)
    total_cols = sum(len(t.get("columns", [])) for t in tables.values())
    numeric, date_cols, cat_cols = [], [], []
    for tname, tdef in tables.items():
        for col in tdef.get("columns", []):
            ctype = col.get("type", "").upper()
            cname = f"{tname}.{col['name']}"
            if any(x in ctype for x in ["INT", "FLOAT", "DECIMAL", "NUMERIC"]):
                numeric.append(cname)
            elif any(x in ctype for x in ["DATE", "TIME", "TIMESTAMP"]):
                date_cols.append(cname)
            elif any(x in ctype for x in ["VARCHAR", "TEXT", "CHAR"]):
                cat_cols.append(cname)
    return {
        "table_count": table_count,
        "total_columns": total_cols,
        "has_foreign_keys": bool(detect_relationships(tables)),
        "has_numeric_columns": bool(numeric),
        "has_date_columns": bool(date_cols),
        "numeric_columns": numeric,
        "categorical_columns": cat_cols,
        "date_columns": date_cols,
        "complexity_score": round(table_count * 1.0 + total_cols * 0.1 + len(date_cols) * 0.3, 2)
    }


def make_schema_doc(schema_id: str, name: str, domain: str,
                    tables: dict, sample_data: dict,
                    difficulty_levels: List[str],
                    sql_categories: List[str],
                    source: str = "open_source") -> dict:
    return {
        "schema_id": schema_id,
        "name": name,
        "domain": domain,
        "difficulty_levels": difficulty_levels,
        "sql_categories": sql_categories,
        "tables": tables,
        "sample_data": sample_data,
        "relationships": detect_relationships(tables),
        "metadata": calc_metadata(tables),
        "usage_count": 0,
        "last_used_at": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "source": source,
        "question_count": 0
    }


# ─────────────────────────────────────────────────────────────
# Source 1: Spider tables.json
# ─────────────────────────────────────────────────────────────

def load_spider_schemas() -> List[dict]:
    """Extract schemas from Spider. Uses tables.json if available, else db_summary.json."""
    tables_file = SPIDER_DIR / "tables.json"
    db_summary_file = SPIDER_DIR / "db_summary.json"
    train_file = SPIDER_DIR / "train_spider.json"

    schemas = []
    seen_sigs = set()

    # Try tables.json first (full schema info)
    if tables_file.exists():
        with open(tables_file) as f:
            spider_dbs = json.load(f)
        print(f"  Using tables.json ({len(spider_dbs)} databases)")
        return _parse_spider_tables_json(spider_dbs, seen_sigs)

    # Fallback: build schemas from train Q&A pairs
    if not train_file.exists():
        print("  ⚠ No Spider data found — skipping")
        return []

    print("  tables.json not available — building schemas from Q&A pairs")
    with open(train_file) as f:
        train_data = json.load(f)

    # Group by db_id
    db_groups = defaultdict(list)
    for item in train_data:
        db_id = item.get("db_id", "")
        if db_id:
            db_groups[db_id].append(item)

    for db_id, items in db_groups.items():
        # Extract table names from SQL queries
        tables = {}
        for item in items[:20]:  # sample first 20 queries
            query = item.get("query", "")
            # Find table names from FROM/JOIN clauses
            tnames = re.findall(
                r'(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                query, re.IGNORECASE
            )
            for tname in tnames:
                if tname.upper() not in ("SELECT", "WHERE", "ON", "AND", "OR"):
                    if tname not in tables:
                        tables[tname] = {"columns": [
                            {"name": "id", "type": "INTEGER", "constraints": "PRIMARY KEY"},
                            {"name": "name", "type": "VARCHAR(255)", "constraints": ""},
                        ]}

        if not tables or len(tables) < 2:
            continue

        sig = schema_signature(tables)
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)

        domain = db_id.replace("_", " ").lower()
        meta = calc_metadata(tables)
        cats = ["select", "join"]
        if meta["table_count"] >= 3:
            cats += ["subquery", "aggregation", "window", "cte"]
        diffs = ["easy", "medium", "hard"]

        schema_id = f"spider_{db_id}_{sig}"
        doc = make_schema_doc(
            schema_id=schema_id,
            name=f"Spider - {db_id.replace('_', ' ').title()}",
            domain=domain,
            tables=tables,
            sample_data={t: [] for t in tables},
            difficulty_levels=diffs,
            sql_categories=list(set(cats)),
            source="spider_yale"
        )
        schemas.append(doc)

    print(f"  ✓ Extracted {len(schemas)} schemas from Spider Q&A pairs")
    return schemas


def _parse_spider_tables_json(spider_dbs: list, seen_sigs: set) -> List[dict]:
    """Parse full Spider tables.json format."""
    schemas = []
    for db in spider_dbs:
        db_id = db.get("db_id", "")
        table_names = db.get("table_names_original", [])
        column_names = db.get("column_names_original", [])
        column_types = db.get("column_types", [])
        primary_keys = set(db.get("primary_keys", []))

        if not table_names:
            continue

        tables = {tname: {"columns": []} for tname in table_names}

        for col_idx, (tbl_idx, col_name) in enumerate(column_names):
            if tbl_idx < 0 or tbl_idx >= len(table_names):
                continue
            tname = table_names[tbl_idx]
            ct = (column_types[col_idx] if col_idx < len(column_types) else "text").lower()
            if ct in ("number", "int", "integer"):
                col_type = "INTEGER"
            elif ct in ("real", "float", "double"):
                col_type = "DECIMAL"
            elif ct in ("text", "varchar", "char"):
                col_type = "VARCHAR(255)"
            elif ct in ("time", "date", "datetime", "timestamp"):
                col_type = "TIMESTAMP"
            elif ct == "boolean":
                col_type = "BOOLEAN"
            else:
                col_type = "TEXT"
            constraint = "PRIMARY KEY" if col_idx in primary_keys else ""
            tables[tname]["columns"].append({
                "name": col_name, "type": col_type, "constraints": constraint
            })

        tables = {k: v for k, v in tables.items() if v["columns"]}
        if not tables:
            continue

        sig = schema_signature(tables)
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)

        domain = db_id.replace("_", " ").lower()
        meta = calc_metadata(tables)
        cats = ["select"]
        if meta["table_count"] >= 2:
            cats += ["join", "subquery"]
        if meta["has_numeric_columns"]:
            cats += ["aggregation"]
        if meta["table_count"] >= 3:
            cats += ["window", "cte"]
        if meta["has_date_columns"]:
            cats += ["date_functions"]
        diffs = ["easy"]
        if meta["table_count"] >= 2:
            diffs.append("medium")
        if meta["table_count"] >= 3 or meta["total_columns"] >= 10:
            diffs.append("hard")

        schemas.append(make_schema_doc(
            schema_id=f"spider_{db_id}_{sig}",
            name=f"Spider - {db_id.replace('_', ' ').title()}",
            domain=domain,
            tables=tables,
            sample_data={t: [] for t in tables},
            difficulty_levels=diffs,
            sql_categories=list(set(cats)),
            source="spider_yale"
        ))

    print(f"  ✓ Extracted {len(schemas)} schemas from Spider tables.json")
    return schemas


# ─────────────────────────────────────────────────────────────
# Source 2: gretelai extended
# ─────────────────────────────────────────────────────────────

def parse_sql_context(sql_context: str):
    """Parse CREATE TABLE + INSERT INTO from gretelai sql_context."""
    schemas = {}
    sample_data = {}

    create_pat = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?[`"]?(\w+)[`"]?\s*\(([^;]+)\)',
        re.IGNORECASE | re.DOTALL
    )
    for tname, cols_raw in create_pat.findall(sql_context):
        columns = []
        for line in cols_raw.split(','):
            line = line.strip()
            if re.match(r'^\s*(PRIMARY|FOREIGN|UNIQUE|CHECK|INDEX|CONSTRAINT)\s+', line, re.I):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            col_name = parts[0].strip('`"[]')
            ct = parts[1].upper()
            if any(x in ct for x in ["INT", "SERIAL", "NUMERIC", "DECIMAL", "NUMBER"]):
                col_type = "INTEGER" if "INT" in ct else "DECIMAL"
            elif any(x in ct for x in ["FLOAT", "DOUBLE", "REAL"]):
                col_type = "DECIMAL"
            elif any(x in ct for x in ["CHAR", "TEXT", "STRING", "VARCHAR"]):
                col_type = "VARCHAR(255)"
            elif "BOOL" in ct:
                col_type = "BOOLEAN"
            elif any(x in ct for x in ["DATE", "TIME", "TIMESTAMP"]):
                col_type = "TIMESTAMP"
            else:
                col_type = "TEXT"
            constraint = ""
            if "PRIMARY KEY" in line.upper():
                constraint = "PRIMARY KEY"
            elif "NOT NULL" in line.upper():
                constraint = "NOT NULL"
            columns.append({"name": col_name, "type": col_type, "constraints": constraint})
        if columns:
            schemas[tname] = {"columns": columns}
            sample_data[tname] = []

    insert_pat = re.compile(
        r'INSERT\s+INTO\s+[`"]?(\w+)[`"]?\s*(?:\(([^)]+)\))?\s*VALUES\s*((?:\([^)]+\)\s*,?\s*)+)',
        re.IGNORECASE | re.DOTALL
    )
    for tname, cols_str, vals_str in insert_pat.findall(sql_context):
        if tname not in schemas:
            continue
        col_names = [c.strip().strip('`"') for c in cols_str.split(',')] if cols_str.strip() \
            else [c["name"] for c in schemas[tname]["columns"]]
        for vtuple in re.findall(r'\(([^)]+)\)', vals_str):
            raw_vals = re.split(r',(?=(?:[^\']*\'[^\']*\')*[^\']*$)', vtuple)
            row = {}
            for cname, rv in zip(col_names, raw_vals):
                v = rv.strip().strip("'\"")
                if v.upper() in ("NULL", "NONE", ""):
                    v = None
                else:
                    try:
                        v = int(v)
                    except ValueError:
                        try:
                            v = float(v)
                        except ValueError:
                            pass
                row[cname] = v
            if row:
                sample_data[tname].append(row)

    return schemas, sample_data


def load_gretelai_schemas(max_schemas: int = 500) -> List[dict]:
    """Extract unique schemas from gretelai dataset."""
    if not GRETELAI_CACHE.exists():
        # Try existing cache
        alt = BASE_DIR / "gretel_sql_cache.parquet"
        if not alt.exists():
            print("  ⚠ gretelai cache not found — run download_open_source_datasets.py first")
            return []
        cache_path = alt
    else:
        cache_path = GRETELAI_CACHE

    import pandas as pd
    df = pd.read_parquet(cache_path)
    print(f"  Loaded {len(df):,} gretelai rows")

    seen_sigs = set()
    schemas = []

    # Complexity → categories + difficulty
    # Actual gretelai column values from download:
    # 'basic SQL', 'aggregation', 'single join', 'subqueries',
    # 'window functions', 'multiple_joins', 'set operations', 'CTEs'
    COMPLEXITY_MAP = {
        "basic sql":        (["select"],                                    ["easy"]),
        "single join":      (["join", "select"],                            ["easy", "medium"]),
        "aggregation":      (["aggregation", "select"],                     ["easy", "medium"]),
        "multiple_joins":   (["join", "aggregation", "subquery"],           ["medium", "hard"]),
        "multiple joins":   (["join", "aggregation", "subquery"],           ["medium", "hard"]),
        "subqueries":       (["subquery", "join"],                          ["medium", "hard"]),
        "window functions": (["window", "aggregation"],                     ["hard"]),
        "ctes":             (["cte", "subquery", "window"],                 ["hard"]),
        "set operations":   (["aggregation", "subquery"],                   ["medium", "hard"]),
        # legacy keys kept for compatibility
        "simple":           (["select"],                                    ["easy"]),
        "complex":          (["subquery", "cte", "window"],                 ["hard"]),
    }

    for _, row in df.iterrows():
        if len(schemas) >= max_schemas:
            break

        sql_context = str(row.get("sql_context", ""))
        if not sql_context:
            continue

        tables, sample_data = parse_sql_context(sql_context)
        if not tables:
            continue

        sig = schema_signature(tables)
        if sig in seen_sigs:
            continue
        seen_sigs.add(sig)

        complexity = str(row.get("sql_complexity", "simple")).lower().strip()
        cats, diffs = COMPLEXITY_MAP.get(complexity, (["select"], ["easy", "medium"]))

        domain = str(row.get("domain", "general")).lower()
        schema_id = f"gretelai_{domain.replace(' ', '_')}_{sig}"

        doc = make_schema_doc(
            schema_id=schema_id,
            name=f"{domain.title()} Database",
            domain=domain,
            tables=tables,
            sample_data=sample_data,
            difficulty_levels=diffs,
            sql_categories=cats,
            source="gretelai_synthetic"
        )
        schemas.append(doc)

    print(f"  ✓ Extracted {len(schemas)} unique schemas from gretelai")
    return schemas
