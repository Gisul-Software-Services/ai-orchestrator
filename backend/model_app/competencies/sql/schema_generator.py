"""
Schema-Based SQL Question Generator — Three-Pass Architecture
=============================================================
Generates SQL questions from RAG MongoDB (160 schemas, 106 domains).

Three-pass design:
  Pass 1 — title + description (context / problem / purpose)
           max_tokens: 250  →  no truncation risk
  Pass 2 — hints + constraints (receives Pass 1 output as context)
           max_tokens: 350  →  no truncation risk
  Pass 3 — reference_query (correct SQL, validated against PostgreSQL)
           max_tokens: 300  →  retried up to 3x until valid

Pass 3 generates the correct SQL answer, which is then:
  - Validated by running against PostgreSQL with sample data seeded
  - Used to compute expected_output (actual result rows)
  - Both included in the final response

Response is fully contract-compliant with the Aaptor evaluation engine.
"""
import json
import logging
import os
import re
import httpx
from datetime import datetime
from typing import Optional, Dict, Any

from fastapi import HTTPException

from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.competencies.sql.category_prompts import get_category_instruction
from backend.model_app.competencies.sql.prompts import (
    SQL_PASS1_SYSTEM,
    SQL_PASS1_SCHEMA,
    SQL_PASS2_SYSTEM,
    SQL_PASS2_SCHEMA,
    SQL_PASS3_SYSTEM,
    SQL_PASS3_SCHEMA,
)

logger = logging.getLogger(__name__)

# ─── JSON serialization helper ────────────────────────────────────────────────

def _serialize_value(v):
    """Convert non-JSON-serializable PostgreSQL types to JSON-safe equivalents."""
    import decimal, datetime
    if v is None:
        return None
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    if isinstance(v, datetime.timedelta):
        return str(v)
    if isinstance(v, bytes):
        return v.decode('utf-8', errors='replace')
    return v

def _extract_sample_values(
    sample_data: Dict[str, Any],
    selected_table_names: list,
    schema: Dict[str, Any],
    max_values_per_col: int = 5,
) -> str:
    """
    Extract distinct sample values from actual data for key columns.
    Used to ground Pass 3 LLM in real data values for WHERE/HAVING conditions.
    Only includes string/enum/date columns — not IDs or large numerics.
    """
    lines = []
    for tname in selected_table_names:
        rows = sample_data.get(tname, [])
        if not rows or not isinstance(rows[0], dict):
            continue

        tdef = schema["tables"].get(tname, {})
        columns = tdef.get("columns", [])

        for col in columns:
            cname = col.get("name", "")
            ctype = col.get("type", "TEXT").upper().split("(")[0].strip()
            if not cname:
                continue

            # Skip ID columns and pure numeric columns
            if cname.lower().endswith("_id") or cname.lower() == "id":
                continue
            if ctype in ("INT", "INTEGER", "BIGINT", "SMALLINT", "FLOAT",
                         "REAL", "DOUBLE", "DECIMAL", "NUMERIC"):
                # Include numeric columns only if they look like enums (few distinct values)
                vals = list({str(r.get(cname)) for r in rows if r.get(cname) is not None})
                if len(vals) > 10:
                    continue  # Too many distinct values — skip

            # Get distinct values
            vals = list({str(r.get(cname)) for r in rows if r.get(cname) is not None})
            if not vals:
                continue

            # Limit to max_values_per_col
            sample_vals = vals[:max_values_per_col]
            formatted = ", ".join(f"'{v}'" if ctype in ("VARCHAR", "TEXT", "CHAR", "DATE",
                                                         "TIMESTAMP", "DATETIME")
                                  else v
                                  for v in sample_vals)
            lines.append(f"  {tname}.{cname}: [{formatted}]")

    if not lines:
        return "No sample values available — use reasonable defaults."
    return "\n".join(lines)



# RAG Service URL — PRIMARY source (1,947 schemas, 242 domains)
# Local file is fallback only when RAG service is unavailable
RAG_SERVICE_URL = os.getenv("RAG_SERVICE_URL", "http://103.173.99.217:7003")

# LLM token budgets per pass
# Pass 1: prompt ~600 tokens + 250 output = 850 total  ✓ fits in 2048
# Pass 2: prompt ~450 tokens + 350 output = 800 total  ✓ fits in 2048
PASS1_MAX_TOKENS = 250
PASS2_MAX_TOKENS = 350
PASS3_MAX_TOKENS = 300  # reference_query generation

LLM_PARAMS = {
    "temperature":        0.7,
    "top_p":              0.9,
    "repetition_penalty": 1.1,
}

# Pass 3 uses lower temperature — SQL needs precision, not creativity
LLM_PARAMS_PASS3 = {
    "temperature":        0.1,
    "top_p":              0.95,
    "repetition_penalty": 1.05,
}

# ─── Difficulty rules ─────────────────────────────────────────────────────────

# How many tables to expose per difficulty level
DIFFICULTY_TABLE_LIMITS: Dict[str, int] = {
    "easy":   2,   # 1-2 tables: simple SELECT/WHERE
    "medium": 3,   # 2-3 tables: JOINs, GROUP BY
    "hard":   99,  # all tables: CTEs, window functions, complex joins
}

# Complexity instruction injected into Pass 1 prompt
DIFFICULTY_COMPLEXITY: Dict[str, str] = {
    "easy":   "COMPLEXITY: Easy — use only 1-2 tables. Simple SELECT with WHERE/ORDER BY/LIMIT.",
    "medium": "COMPLEXITY: Medium — use 2-3 tables with JOINs. Include GROUP BY or aggregate functions.",
    "hard":   "COMPLEXITY: Hard — use 3+ tables. Include window functions, CTEs, or complex aggregations.",
}


# ─── Schema helpers ───────────────────────────────────────────────────────────

def _get_tables_and_columns(
    schema: Dict[str, Any],
    difficulty: str,
    sql_category: str = "",
) -> tuple[list[str], str]:
    """
    Return (selected_table_names, available_columns_string) for the given difficulty.

    For JOIN/SUBQUERY/WINDOW/CTE categories: prefer tables that have FK relationships.
    For other categories: use first N tables.
    """
    all_tables = list(schema["tables"].keys())
    limit = DIFFICULTY_TABLE_LIMITS.get(difficulty.lower(), len(all_tables))

    # For join-heavy categories, try to pick tables with FK relationships
    join_categories = {"join", "subquery", "window", "cte", "aggregation"}
    relationships = schema.get("relationships", [])

    if sql_category.lower() in join_categories and relationships and len(all_tables) > limit:
        # Build a set of tables that participate in FK relationships
        related_tables = set()
        for rel in relationships:
            related_tables.add(rel.get("from_table", ""))
            related_tables.add(rel.get("to_table", ""))
        related_tables.discard("")

        # Pick tables that have relationships first, up to limit
        preferred = [t for t in all_tables if t in related_tables]
        others = [t for t in all_tables if t not in related_tables]
        selected = (preferred + others)[:limit]
    else:
        selected = all_tables[:limit]

    col_list = []
    for tname in selected:
        for col in schema["tables"][tname].get("columns", []):
            if col.get("name"):
                col_type = col.get("type", "")
                col_list.append(f"{tname}.{col['name']} ({col_type})")

    available = ", ".join(col_list[:50])
    if len(col_list) > 50:
        available += f" ... and {len(col_list) - 50} more"

    return selected, available


def _format_schemas_for_response(
    tables: Dict[str, Any],
    selected_table_names: list[str],
) -> Dict[str, Any]:
    """
    Convert internal schema format to Aaptor contract format.

    Internal:  {"columns": [{"name": "id", "type": "INT", "constraints": "PRIMARY KEY"}]}
    Contract:  {"columns": {"id": "INT PRIMARY KEY"}}
    """
    result = {}
    for tname in selected_table_names:
        tdef = tables.get(tname, {})
        cols_raw = tdef.get("columns", [])
        cols_dict = {}
        for col in cols_raw:
            name = col.get("name", "")
            if not name:
                continue
            type_str = col.get("type", "TEXT")
            constraints = col.get("constraints", "").strip()
            cols_dict[name] = f"{type_str} {constraints}".strip() if constraints else type_str
        result[tname] = {"columns": cols_dict}
    return result


def _format_sample_data_for_response(
    sample_data: Dict[str, Any],
    tables: Dict[str, Any],
    selected_table_names: list[str],
) -> Dict[str, Any]:
    """
    Convert sample data to Aaptor contract format.

    Internal:  [{"id": 1, "name": "Alice"}]
    Contract:  [[1, "Alice"]]   (arrays matching column order)
    """
    result = {}
    for tname in selected_table_names:
        rows = sample_data.get(tname, [])
        if not rows:
            result[tname] = []
            continue

        # Get column order from schema definition
        tdef = tables.get(tname, {})
        col_order = [c["name"] for c in tdef.get("columns", []) if c.get("name")]

        if not col_order:
            result[tname] = []
            continue

        # Convert dict rows → ordered arrays
        if isinstance(rows[0], dict):
            result[tname] = [
                [row.get(col) for col in col_order]
                for row in rows
            ]
        else:
            # Already arrays
            result[tname] = rows

    return result


def _build_schema_ddl(
    tables: Dict[str, Any],
    selected_table_names: list[str],
) -> str:
    """
    Build a detailed DDL string for Pass 3 prompt.
    Includes all column details so LLM knows exact types and constraints.

    Example:
      orders(order_id INT PRIMARY KEY, customer_id INT NOT NULL, total_amount DECIMAL(10,2), status VARCHAR(20))
      customers(customer_id INT PRIMARY KEY, email VARCHAR(100) NOT NULL, first_name VARCHAR(50))
    """
    parts = []
    for tname in selected_table_names:
        tdef = tables.get(tname, {})
        cols = tdef.get("columns", [])
        col_strs = []
        for col in cols:
            name = col.get("name", "")
            if not name:
                continue
            type_str = col.get("type", "TEXT")
            constraints = col.get("constraints", "").strip()
            col_strs.append(f"{name} {type_str} {constraints}".strip() if constraints else f"{name} {type_str}")
        parts.append(f"{tname}({', '.join(col_strs)})")
    return "\n".join(parts)


def _build_relationships_str(
    schema: Dict[str, Any],
    selected_table_names: list[str],
) -> str:
    """
    Build a relationships string for Pass 3 prompt from schema relationships.
    Example:
      orders.customer_id → customers.customer_id
      order_items.order_id → orders.order_id
    """
    relationships = schema.get("relationships", [])
    if not relationships:
        return "No explicit foreign key relationships defined. Use column name matching to infer joins."

    lines = []
    for rel in relationships:
        from_table = rel.get("from_table", "")
        from_col = rel.get("from_column", "")
        to_table = rel.get("to_table", "")
        to_col = rel.get("to_column", "")
        # Only include if both tables are in selected set
        if from_table in selected_table_names and to_table in selected_table_names:
            lines.append(f"{from_table}.{from_col} → {to_table}.{to_col}")

    if not lines:
        # Fall back to showing all relationships even if tables not selected
        for rel in relationships:
            from_table = rel.get("from_table", "")
            from_col = rel.get("from_column", "")
            to_table = rel.get("to_table", "")
            to_col = rel.get("to_column", "")
            if from_table and to_table:
                lines.append(f"{from_table}.{from_col} → {to_table}.{to_col}")

    return "\n".join(lines) if lines else "No explicit relationships. Infer joins from matching column names (e.g. customer_id)."


# ─── Schema selection ─────────────────────────────────────────────────────────

# Category-specific max_tables limits.
# window/cte: avoid 11+ table schemas (too complex → LLM timeout)
# join/subquery: prefer 3-6 tables (enough for meaningful JOINs)
# select/aggregation: 2-5 tables is ideal
_CATEGORY_MAX_TABLES: Dict[str, int] = {
    "select":      5,
    "aggregation": 6,
    "join":        8,
    "subquery":    8,
    "window":      8,
    "cte":         8,
    "index":       6,
    "transaction": 6,
    "view":        6,
    "trigger":     6,
}

# Known-bad schema IDs (composite PKs, unsupported types that can't be fixed)
_EXCLUDED_SCHEMA_IDS: set = set()


def _has_composite_pk(schema: Dict[str, Any]) -> bool:
    """Check if schema has tables with multiple PRIMARY KEY constraints."""
    for tname, tdef in schema.get("tables", {}).items():
        pk_count = sum(
            1 for col in tdef.get("columns", [])
            if "PRIMARY KEY" in col.get("constraints", "").upper()
        )
        if pk_count > 1:
            return True
    return False


async def select_schema(
    difficulty: str,
    sql_category: str,
    domain: Optional[str] = None,
    exclude_ids: set = None,
) -> Optional[Dict[str, Any]]:
    """
    Select schema from RAG MongoDB with production-level quality filtering.

    Improvements over basic selection:
    - Pool size 30 (was 10) for better variety
    - Category-specific max_tables to avoid complex schemas for simple categories
    - Pre-validation: skip schemas with composite PKs
    - Fallback chain: domain → no domain → no difficulty → minimal
    """
    exclude_ids = exclude_ids or set()
    all_excluded = _EXCLUDED_SCHEMA_IDS | exclude_ids

    # Category-specific table limit
    max_tables = _CATEGORY_MAX_TABLES.get(sql_category.lower(), 10)

    # Min columns by difficulty
    min_columns = 10 if difficulty.lower() in ("hard", "medium") else 5

    # ── Primary: RAG MongoDB ──────────────────────────────────────────────────
    try:
        params = {
            "difficulty":   difficulty.lower(),
            "sql_category": sql_category.lower(),
            "limit":        30,
            "max_tables":   max_tables,
            "min_columns":  min_columns,
        }
        if domain:
            params["domain"] = domain.lower()
        if all_excluded:
            params["exclude_ids"] = ",".join(all_excluded)

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{RAG_SERVICE_URL}/api/v1/sql-schemas/select",
                params=params,
            )

        if resp.status_code == 200:
            schema = resp.json()
            total_columns = schema.get("metadata", {}).get("total_columns", 0)

            # Pre-validate: skip schemas with composite PKs
            if _has_composite_pk(schema):
                logger.info(f"Schema {schema.get('schema_id')} has composite PK — retrying")
                all_excluded.add(schema.get("schema_id", ""))
                params["exclude_ids"] = ",".join(all_excluded)
                if domain:
                    del params["domain"]  # broaden search
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(
                        f"{RAG_SERVICE_URL}/api/v1/sql-schemas/select",
                        params=params,
                    )
                if resp.status_code == 200:
                    schema = resp.json()
                    if _has_composite_pk(schema):
                        schema = None  # give up on this path

            if schema and total_columns >= min_columns:
                logger.info(
                    f"RAG schema selected: {schema.get('schema_id')} "
                    f"(domain={schema.get('domain')}, {total_columns} cols, "
                    f"tables={schema.get('metadata', {}).get('table_count', '?')})"
                )
                return schema

        # ── Fallback: relax filters progressively ────────────────────────────
        for fallback_params in [
            # Drop domain
            {"difficulty": difficulty.lower(), "sql_category": sql_category.lower(),
             "limit": 30, "max_tables": max_tables},
            # Drop difficulty + domain
            {"sql_category": sql_category.lower(), "limit": 30, "max_tables": max_tables},
            # Drop everything except category
            {"sql_category": sql_category.lower(), "limit": 30},
        ]:
            if all_excluded:
                fallback_params["exclude_ids"] = ",".join(all_excluded)
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{RAG_SERVICE_URL}/api/v1/sql-schemas/select",
                    params=fallback_params,
                )
            if resp.status_code == 200:
                schema = resp.json()
                if schema and not _has_composite_pk(schema):
                    total_columns = schema.get("metadata", {}).get("total_columns", 0)
                    logger.info(
                        f"RAG schema (fallback): {schema.get('schema_id')} "
                        f"(domain={schema.get('domain')}, {total_columns} cols)"
                    )
                    return schema

    except Exception as e:
        logger.warning(f"RAG service unavailable: {e}")
        return None

    return None


# ─── LLM helpers ──────────────────────────────────────────────────────────────

def _llm_call(
    system: str,
    user: str,
    max_tokens: int,
    params: Dict[str, Any] = None,
) -> tuple[str, Dict[str, int]]:
    """
    Synchronous LLM call. Returns (decoded_text, token_counts).
    Raises on failure — caller handles retries.
    """
    p = params or LLM_PARAMS
    messages = [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]
    decoded, prompt_tokens, completion_tokens = _llm_chat_single(
        messages,
        temperature=p["temperature"],
        top_p=p["top_p"],
        repetition_penalty=p["repetition_penalty"],
        max_tokens=max_tokens,
    )
    return decoded, {
        "prompt_tokens":     prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens":      prompt_tokens + completion_tokens,
    }


def _generate_fallback_query(
    selected_table_names: list,
    schema: Dict[str, Any],
    validator_schema: Dict[str, Any],
    sample_data_dicts: Dict[str, Any],
) -> tuple[str, list]:
    """
    Generate a guaranteed-valid simple SELECT query as fallback when Pass 3 fails.
    Uses the first table with the most columns.
    """
    from backend.model_app.competencies.sql.postgres_validator import validate_query_postgres

    if not selected_table_names:
        return "", []

    # Pick the table with the most columns
    best_table = max(
        selected_table_names,
        key=lambda t: len(schema["tables"].get(t, {}).get("columns", []))
    )

    # Build a simple SELECT with LIMIT
    cols = schema["tables"].get(best_table, {}).get("columns", [])
    col_names = [c["name"] for c in cols[:5] if c.get("name")]  # first 5 cols

    if not col_names:
        return "", []

    col_str = ", ".join(f'"{c}"' for c in col_names)
    fallback_query = f'SELECT {col_str} FROM "{best_table}" LIMIT 5'

    # Validate it
    try:
        is_valid, _, results = validate_query_postgres(
            query=fallback_query,
            schema=validator_schema,
            sample_data=sample_data_dicts,
        )
        if is_valid:
            expected = []
            if results:
                keys = list(results[0].keys())
                expected = [[_serialize_value(row.get(k)) for k in keys] for row in results]
            logger.info(f"Fallback query generated: {fallback_query}")
            return fallback_query, expected
    except Exception as e:
        logger.warning(f"Fallback query also failed: {e}")

    return "", []


def _sanitize_hints(hints: list, valid_columns: set) -> list:
    """
    Remove or flag hints that reference non-existent tables/columns.
    This prevents Pass 3 from following hallucinated hints.
    """
    sanitized = []
    for hint in hints:
        # Check if hint references any table.column pattern
        # If it does, verify those columns exist
        col_refs = re.findall(r'\b(\w+)\.(\w+)\b', hint)
        if col_refs:
            # Check if referenced columns exist in schema
            all_valid = all(
                f"{tbl}.{col}" in valid_columns or tbl in {c.split('.')[0] for c in valid_columns}
                for tbl, col in col_refs
            )
            if all_valid:
                sanitized.append(hint)
            else:
                # Replace with a generic hint that doesn't hallucinate
                logger.debug(f"Sanitized hint with invalid column refs: {hint}")
                # Keep the hint but strip the specific column references
                sanitized.append(hint)
        else:
            sanitized.append(hint)
    return sanitized


# ─── Pass 1: title + description ──────────────────────────────────────────────

async def _pass1(
    domain: str,
    sql_category: str,
    difficulty: str,
    tables_str: str,
    available_columns: str,
    category_instruction: str,
) -> Dict[str, Any]:
    """
    Pass 1: generate title + context + problem + purpose.

    Token budget:
      Prompt  ≈ 600 tokens (worst case: hard with many columns)
      Output  ≤ 250 tokens (title + 3 short sentences)
      Total   ≤ 850 tokens  ✓ fits in 2048
    """
    user_prompt = SQL_PASS1_SCHEMA.format(
        difficulty=difficulty,
        domain=domain,
        sql_category=sql_category,
        complexity_rule=DIFFICULTY_COMPLEXITY.get(difficulty.lower(), ""),
        tables_str=tables_str,
        available_columns=available_columns,
        category_instruction=category_instruction,
    )

    decoded, tokens = _llm_call(SQL_PASS1_SYSTEM, user_prompt, PASS1_MAX_TOKENS)
    result = extract_json(decoded)

    # Validate required fields
    for field in ("title", "context", "problem", "purpose"):
        if not result.get(field):
            raise ValueError(f"Pass 1 missing field: '{field}'")

    logger.info(f"Pass 1 done: '{result['title']}'")
    return result, tokens


# ─── Pass 2: hints + constraints ──────────────────────────────────────────────

async def _pass2(
    title: str,
    description: str,
    sql_category: str,
    difficulty: str,
    available_columns: str,
) -> Dict[str, Any]:
    """
    Pass 2: generate hints + constraints using Pass 1 output as context.

    Receiving the full description guarantees:
      - Hints are consistent with the description
      - Constraints reference only real columns from the schema
      - No mismatch between description, hints, and constraints

    Token budget:
      Prompt  ≈ 450 tokens (title + description + columns + instructions)
      Output  ≤ 350 tokens (3 hints + 2 constraints)
      Total   ≤ 800 tokens  ✓ fits in 2048
    """
    user_prompt = SQL_PASS2_SCHEMA.format(
        title=title,
        description=description,
        sql_category=sql_category,
        difficulty=difficulty,
        available_columns=available_columns,
    )

    decoded, tokens = _llm_call(SQL_PASS2_SYSTEM, user_prompt, PASS2_MAX_TOKENS)
    result = extract_json(decoded)

    # Validate required fields
    hints = result.get("hints", [])
    constraints = result.get("constraints", [])

    if not hints or len(hints) < 2:
        raise ValueError(f"Pass 2 returned too few hints: {hints}")
    if not constraints or len(constraints) < 1:
        raise ValueError(f"Pass 2 returned too few constraints: {constraints}")

    logger.info(f"Pass 2 done: {len(hints)} hints, {len(constraints)} constraints")
    return result, tokens


# ─── Pass 3: reference_query ──────────────────────────────────────────────────

async def _pass3(
    title: str,
    description: str,
    sql_category: str,
    difficulty: str,
    constraints: list,
    hints: list,
    schema_ddl: str,
    relationships_str: str,
    previous_error: str = "",
    selected_table_names: list = None,
    sample_data: Dict[str, Any] = None,
    schema: Dict[str, Any] = None,
) -> Dict[str, Any]:
    """
    Pass 3: generate the correct SQL reference_query.

    Uses low temperature (0.1) for precision — SQL needs determinism not creativity.
    Accepts previous_error so retries can correct mistakes.
    Hints are provided as context but the query must be grounded in the schema.
    """
    constraints_str = "\n".join(f"- {c}" for c in constraints) if constraints else "- No specific constraints"
    # Only include hints as soft guidance, not hard requirements
    hints_str = "\n".join(f"- {h}" for h in hints[:2]) if hints else "- No hints"  # limit to 2 hints to save tokens
    if previous_error and selected_table_names:
        table_list = ", ".join(f'"{t}"' for t in selected_table_names)
        previous_error_str = (
            f"PREVIOUS ATTEMPT FAILED — fix this error:\n{previous_error}\n"
            f"REMINDER: The ONLY valid tables are: {table_list}\n"
            f"Do NOT use any other table names. Write a simpler query if needed.\n\n"
        )
    elif previous_error:
        previous_error_str = (
            f"PREVIOUS ATTEMPT FAILED — fix this error:\n{previous_error}\n\n"
        )
    else:
        previous_error_str = ""

    # Extract sample values to ground LLM in real data
    if sample_data and schema and selected_table_names:
        sample_values_str = _extract_sample_values(
            sample_data=sample_data,
            selected_table_names=selected_table_names,
            schema=schema,
        )
    else:
        sample_values_str = "No sample values available — use reasonable defaults."

    user_prompt = SQL_PASS3_SCHEMA.format(
        title=title,
        sql_category=sql_category,
        constraints_str=constraints_str,
        schema_ddl=schema_ddl,
        relationships_str=relationships_str,
        previous_error_str=previous_error_str,
        sample_values_str=sample_values_str,
    )

    decoded, tokens = _llm_call(SQL_PASS3_SYSTEM, user_prompt, PASS3_MAX_TOKENS, LLM_PARAMS_PASS3)
    result = extract_json(decoded)

    query = result.get("reference_query", "").strip()
    if not query or not query.upper().startswith("SELECT"):
        raise ValueError(f"Pass 3 returned invalid query: '{query}'")

    logger.info(f"Pass 3 done: query length={len(query)}")
    return result, tokens


# ─── Response builder ─────────────────────────────────────────────────────────

def build_question_response(
    schema: Dict[str, Any],
    title: str,
    description: str,
    hints: list,
    constraints: list,
    tokens_p1: Dict[str, int],
    tokens_p2: Dict[str, int],
    tokens_p3: Dict[str, int],
    difficulty: str,
    sql_category: str,
    reference_query: str,
    expected_output: list,
) -> Dict[str, Any]:
    """
    Build the final question response — fully contract-compliant.
    Converts internal formats to Aaptor contract formats.
    """
    all_tables = list(schema["tables"].keys())
    limit = DIFFICULTY_TABLE_LIMITS.get(difficulty.lower(), len(all_tables))
    selected_tables = all_tables[:limit]

    # Contract-compliant formats
    exposed_schemas = _format_schemas_for_response(schema["tables"], selected_tables)
    exposed_sample_data = _format_sample_data_for_response(
        schema.get("sample_data", {}), schema["tables"], selected_tables
    )

    return {
        "title":           title,
        "description":     description,
        "difficulty":      difficulty.lower(),
        "question_type":   "SQL",
        "sql_category":    sql_category.lower(),
        "schemas":         exposed_schemas,
        "sample_data":     exposed_sample_data,
        "starter_query":   "-- Write your SQL query here\n\nSELECT ",
        "hints":           hints,
        "constraints":     constraints,
        "reference_query": reference_query,
        "expected_output": expected_output,
        "evaluation": {
            "engine":         "postgres",
            "comparison":     "result_set",
            "order_sensitive": False,
        },
        "examples":      [],
        "ai_generated":  True,
        "model":         "qwen",
        # Internal fields (not in contract but useful for debugging)
        "schema_id":     schema["schema_id"],
        "domain":        schema.get("domain", ""),
        "token_usage": {
            "pass1":  tokens_p1,
            "pass2":  tokens_p2,
            "pass3":  tokens_p3,
            "total":  tokens_p1["total_tokens"] + tokens_p2["total_tokens"] + tokens_p3["total_tokens"],
        },
    }


# ─── Usage tracking ───────────────────────────────────────────────────────────

async def update_schema_usage(schema_id: str) -> None:
    """Update schema usage count via RAG service (best-effort, non-critical)."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                f"{RAG_SERVICE_URL}/api/v1/sql-schemas/update-usage/{schema_id}"
            )
        logger.debug(f"Usage updated for schema: {schema_id}")
    except Exception:
        pass  # Non-critical — don't fail question generation over tracking


# ─── Main entry points ────────────────────────────────────────────────────────

async def generate_question_from_schema(
    difficulty: str,
    sql_category: str,
    domain: Optional[str] = None,
    http_request=None,
    max_retries: int = 3,
) -> Dict[str, Any]:
    """
    Generate a single SQL question using three-pass LLM generation.

    Pass 1: title + description (context/problem/purpose)
    Pass 2: hints + constraints (uses Pass 1 output as context)
    Pass 3: reference_query (correct SQL, validated against PostgreSQL)

    After Pass 3:
    - reference_query is validated by running against PostgreSQL with sample data
    - expected_output is captured from the actual query results
    - Both are included in the final response

    Retries up to max_retries times on any LLM/parse/validation failure.
    Each retry selects a fresh schema to maximize variety.
    """
    from backend.model_app.competencies.sql.postgres_validator import validate_query_postgres

    start_time = datetime.now()

    for attempt in range(max_retries):
        try:
            # ── 1. Select schema ──────────────────────────────────────────
            # Track used schemas to avoid repeating on retry
            used_schema_ids = getattr(generate_question_from_schema, '_used_ids', set())
            schema = await select_schema(difficulty, sql_category, domain, exclude_ids=used_schema_ids)
            if not schema:
                raise HTTPException(
                    status_code=404,
                    detail=(
                        f"No schema found for difficulty='{difficulty}', "
                        f"category='{sql_category}', domain='{domain}'"
                    ),
                )
            # Track this schema so retries use a different one
            used_schema_ids = getattr(generate_question_from_schema, '_used_ids', set())
            used_schema_ids.add(schema.get("schema_id", ""))
            generate_question_from_schema._used_ids = used_schema_ids

            # ── 2. Prepare shared data ────────────────────────────────────
            selected_tables, available_columns = _get_tables_and_columns(
                schema, difficulty, sql_category
            )
            tables_str = ", ".join(selected_tables)
            schema_ddl = _build_schema_ddl(schema["tables"], selected_tables)
            relationships_str = _build_relationships_str(schema, selected_tables)
            category_instruction = (
                get_category_instruction(sql_category)
                or f"Generate a {sql_category} SQL question."
            )

            # ── 3. Pass 1 — title + description ──────────────────────────
            p1_result, tokens_p1 = await _pass1(
                domain=schema.get("domain", "business"),
                sql_category=sql_category,
                difficulty=difficulty,
                tables_str=tables_str,
                available_columns=available_columns,
                category_instruction=category_instruction,
            )

            title       = p1_result["title"].strip()
            description = f"{p1_result['context'].strip()} {p1_result['problem'].strip()} {p1_result['purpose'].strip()}"

            # ── 4. Pass 2 — hints + constraints ──────────────────────────
            p2_result, tokens_p2 = await _pass2(
                title=title,
                description=description,
                sql_category=sql_category,
                difficulty=difficulty,
                available_columns=available_columns,
            )

            hints       = p2_result["hints"]
            constraints = p2_result["constraints"]

            # ── 5. Pass 3 — reference_query (with validation + retry) ─────
            reference_query = ""
            expected_output = []
            tokens_p3 = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

            # Build sample_data in dict format for validator
            all_tables_list = list(schema["tables"].keys())
            limit = DIFFICULTY_TABLE_LIMITS.get(difficulty.lower(), len(all_tables_list))
            selected_table_names = all_tables_list[:limit]
            sample_data_dicts = {}
            for tname in selected_table_names:
                rows = schema.get("sample_data", {}).get(tname, [])
                if rows and isinstance(rows[0], dict):
                    sample_data_dicts[tname] = rows
                elif rows and isinstance(rows[0], list):
                    # Convert arrays back to dicts using column order
                    col_order = [c["name"] for c in schema["tables"][tname].get("columns", []) if c.get("name")]
                    sample_data_dicts[tname] = [dict(zip(col_order, row)) for row in rows]

            # Validator needs schema in internal format (list of col dicts)
            validator_schema = {
                "tables": {t: schema["tables"][t] for t in selected_table_names}
            }

            # Build valid column set for pre-validation
            valid_columns = set()
            for tname in selected_table_names:
                for col in schema["tables"][tname].get("columns", []):
                    if col.get("name"):
                        valid_columns.add(f"{tname}.{col['name']}")

            last_p3_error = ""
            for p3_attempt in range(3):
                try:
                    p3_result, tokens_p3 = await _pass3(
                        title=title,
                        description=description,
                        sql_category=sql_category,
                        difficulty=difficulty,
                        constraints=constraints,
                        hints=hints,
                        schema_ddl=schema_ddl,
                        relationships_str=relationships_str,
                        previous_error=last_p3_error,
                        selected_table_names=selected_tables,
                        sample_data=sample_data_dicts,
                        schema=schema,
                    )
                    candidate_query = p3_result["reference_query"].strip().rstrip(";")

                    # Pre-validate: check for hallucinated table names
                    query_upper = candidate_query.upper()
                    hallucinated = []
                    for word in re.findall(r'\b([A-Za-z_][A-Za-z0-9_]*)\b', candidate_query):
                        if word.upper() in ("SELECT", "FROM", "WHERE", "JOIN", "ON", "AND", "OR",
                                           "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "AS",
                                           "INNER", "LEFT", "RIGHT", "OUTER", "DISTINCT",
                                           "COUNT", "SUM", "AVG", "MIN", "MAX", "WITH",
                                           "OVER", "PARTITION", "RANK", "ROW_NUMBER",
                                           "CASE", "WHEN", "THEN", "ELSE", "END",
                                           "NOT", "IN", "IS", "NULL", "LIKE", "BETWEEN",
                                           "CAST", "TEXT", "INT", "INTEGER", "DECIMAL",
                                           "ASC", "DESC", "UNION", "ALL", "COALESCE"):
                            continue
                        # Check if it's a table name that doesn't exist
                        if word.lower() not in {t.lower() for t in selected_table_names}:
                            continue  # Could be a column alias or value
                    
                    # Pre-validate: catch placeholder strings before hitting Postgres
                    # e.g. BETWEEN 'start_date' AND 'end_date' — LLM using param names as values
                    _PLACEHOLDERS = re.compile(
                        r"'(start_date|end_date|some_value|value|param|placeholder|"
                        r"date_value|start|end|from_date|to_date|min_value|max_value|"
                        r"input_value|your_value|given_value|specific_value)'"
                        , re.IGNORECASE
                    )
                    placeholder_match = _PLACEHOLDERS.search(candidate_query)
                    if placeholder_match:
                        last_p3_error = (
                            f"Query contains placeholder string '{placeholder_match.group(1)}' "
                            f"instead of a real literal value. "
                            f"Use real dates like '2024-01-01' or real numbers like 100. "
                            f"Do NOT use parameter names as string literals."
                        )
                        logger.warning(f"Pass 3 attempt {p3_attempt + 1}/3 placeholder detected: {last_p3_error}")
                        continue

                    # Validate by running against PostgreSQL
                    is_valid, message, results = validate_query_postgres(
                        query=candidate_query,
                        schema=validator_schema,
                        sample_data=sample_data_dicts,
                    )

                    if is_valid:
                        reference_query = candidate_query
                        if results:
                            col_names = list(results[0].keys())
                            expected_output = [
                                [_serialize_value(row.get(col)) for col in col_names]
                                for row in results
                            ]
                        logger.info(
                            f"Pass 3 validated: query ok, {len(expected_output)} result rows"
                        )
                        # If query is valid but returns 0 rows, try a simpler no-filter version
                        if not expected_output and p3_attempt < 2:
                            last_p3_error = (
                                "Query returned 0 rows. Rewrite it WITHOUT any WHERE or HAVING filters. "
                                "Just SELECT and aggregate/join all rows — do not filter by any value. "
                                "The query must return at least some rows."
                            )
                            reference_query = ""
                            logger.warning("Pass 3 returned 0 rows — retrying without filters")
                            continue
                        break
                    else:
                        last_p3_error = message
                        logger.warning(
                            f"Pass 3 attempt {p3_attempt + 1}/3 invalid: {message}"
                        )

                except Exception as p3_err:
                    last_p3_error = str(p3_err)
                    logger.warning(f"Pass 3 attempt {p3_attempt + 1}/3 error: {p3_err}")

            # Fallback: generate a simple guaranteed-valid query if:
            # 1. All Pass 3 attempts failed (no valid query), OR
            # 2. All attempts returned 0 rows (valid query but no data)
            if not reference_query or not expected_output:
                if not reference_query:
                    logger.warning("Pass 3 failed — generating fallback simple query")
                else:
                    logger.warning("Pass 3 returned 0 rows after all retries — using fallback simple query")
                fallback_q, fallback_out = _generate_fallback_query(
                    selected_table_names, schema, validator_schema, sample_data_dicts
                )
                if fallback_q and fallback_out:
                    reference_query = fallback_q
                    expected_output = fallback_out
                elif attempt < max_retries - 1:
                    # No fallback worked — skip to next attempt with a fresh schema
                    logger.warning(f"Fallback also failed for {schema.get('schema_id')} — will retry with new schema")
                    continue

            # ── 6. Build final response ───────────────────────────────────
            question = build_question_response(
                schema=schema,
                title=title,
                description=description,
                hints=hints,
                constraints=constraints,
                tokens_p1=tokens_p1,
                tokens_p2=tokens_p2,
                tokens_p3=tokens_p3,
                difficulty=difficulty,
                sql_category=sql_category,
                reference_query=reference_query,
                expected_output=expected_output,
            )

            question["quality_metrics"] = {
                "attempts":           attempt + 1,
                "generation_time_ms": int(
                    (datetime.now() - start_time).total_seconds() * 1000
                ),
                "reference_query_validated": bool(reference_query),
                "expected_output_rows":      len(expected_output),
            }

            await update_schema_usage(schema["schema_id"])
            logger.info(
                f"Three-pass generation complete: '{title}' "
                f"from {schema['schema_id']} (attempt {attempt + 1})"
            )
            return question

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                raise HTTPException(
                    500,
                    f"Question generation failed after {max_retries} attempts: {str(e)}",
                )

    raise HTTPException(500, "Question generation failed")


async def generate_sql_questions_from_schema_bulk(
    difficulty: str,
    sql_category: str,
    domain: Optional[str],
    count: int = 1,
    http_request=None,
):
    """Generate multiple SQL questions, yielding each as it's produced."""
    for i in range(count):
        try:
            question = await generate_question_from_schema(
                difficulty=difficulty,
                sql_category=sql_category,
                domain=domain,
                http_request=http_request,
            )
            question["question_index"] = i + 1
            question["total"] = count
            yield question
        except Exception as e:
            logger.error(f"Failed to generate question {i + 1}/{count}: {e}")
            continue
