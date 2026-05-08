"""
SQL Question Generation Prompts — Three-Pass Architecture
==========================================================
Three-pass generation to fit within 2048-token vLLM context:

  Pass 1 — title + description (context / problem / purpose)
           Input:  schema columns, difficulty, category
           Output: { title, context, problem, purpose }
           max_tokens: 250

  Pass 2 — hints + constraints
           Input:  Pass 1 output (title + description) + schema columns
           Output: { hints, constraints }
           max_tokens: 350

  Pass 3 — reference_query (correct SQL answer)
           Input:  title + description + constraints + full schema DDL
           Output: { reference_query }
           max_tokens: 300

Key design principle:
  Pass 2 receives the FULL description from Pass 1 as input.
  Pass 3 receives title + description + constraints to generate a verified SQL answer.
"""
from __future__ import annotations

# ─── Pass 1 ───────────────────────────────────────────────────────────────────

SQL_PASS1_SYSTEM = """You are an expert SQL question generator for a technical assessment platform.
Return ONLY valid JSON. No markdown, no code fences, no extra text.
Rules:
- context, problem, purpose must each be exactly ONE complete sentence.
- Do NOT mention any table names or column names in context, problem, or purpose.
- Do NOT use "you" or "your". Write in strict third-person.
- title must be a realistic business scenario title, not a SQL description."""


SQL_PASS1_SCHEMA = """Generate a SQL question title and description for a {difficulty} level candidate.

Domain: {domain}
Category: {sql_category}
{complexity_rule}

AVAILABLE TABLES: {tables_str}

COLUMNS (for reference — do NOT mention these in the description):
{available_columns}

{category_instruction}

DESCRIPTION FIELDS:
context: One sentence describing the business system and what it manages.
problem: One sentence stating what specific data needs to be found or calculated.
purpose: One sentence stating what the result will be used for.

Return ONLY this JSON:
{{
  "title": "Realistic business scenario title (10-80 chars)",
  "context": "One sentence about the business system.",
  "problem": "One sentence about what needs to be found.",
  "purpose": "One sentence about what the result is used for."
}}"""


# ─── Pass 2 ───────────────────────────────────────────────────────────────────

SQL_PASS2_SYSTEM = """You are an expert SQL question generator for a technical assessment platform.
Return ONLY valid JSON. No markdown, no code fences, no extra text.
CRITICAL RULES:
- hints MUST reference ONLY the exact table.column names from the COLUMNS list provided.
- constraints MUST use ONLY columns that exist in the COLUMNS list. Do NOT invent columns.
- hints and constraints MUST be consistent with the title and description provided.
- constraints must be business rules, NOT SQL syntax instructions.
- Do NOT mention any table or column that is not in the COLUMNS list.
- Do NOT invent tables like 'order_items', 'line_items', 'categories' unless they appear in COLUMNS."""


SQL_PASS2_SCHEMA = """Given this SQL question, generate hints and constraints.

Title: {title}
Description: {description}
Category: {sql_category}
Difficulty: {difficulty}

AVAILABLE TABLES AND COLUMNS (use ONLY these — do NOT invent any other tables or columns):
{available_columns}

HINTS — 3 required:
- Each hint must guide the candidate step by step toward the solution.
- Each hint MUST reference at least one specific table.column from the list above.
- Do NOT mention any table or column not in the list above.
- Hints must be directly relevant to the title and description above.

CONSTRAINTS — 2 required:
- Write business rules that filter or shape the result (e.g. "Only include active accounts").
- Use ONLY column names that exist in the list above.
- Do NOT write SQL syntax instructions (e.g. "Use INNER JOIN" is forbidden).
- Must be consistent with the description above.
- Do NOT reference columns that don't exist in the list above.

Return ONLY this JSON:
{{
  "hints": [
    "Hint 1 referencing exact table.column from the list",
    "Hint 2 referencing exact table.column from the list",
    "Hint 3 referencing exact table.column from the list"
  ],
  "constraints": [
    "Business rule using a real column from the list",
    "Business rule using a real column from the list"
  ]
}}"""


# ─── Pass 3: reference_query ──────────────────────────────────────────────────

SQL_PASS3_SYSTEM = """You are an expert SQL engineer writing correct, executable PostgreSQL queries.
Return ONLY valid JSON. No markdown, no code fences, no extra text.
CRITICAL RULES:
- Use ONLY the exact table names and column names listed in the SCHEMA section.
- Do NOT invent table names, column names, or relationships not shown in SCHEMA.
- If a JOIN is needed, use ONLY the foreign key relationships shown in RELATIONSHIPS.
- If no FK relationship exists between tables, write a single-table query instead.
- The query must be directly executable against the schema as given.
- No semicolons inside the JSON string.
- Aliases must be snake_case.
- When joining columns of different types, use explicit CAST: col::TEXT.
- If unsure about a JOIN, write a simpler single-table aggregation query instead.
- NEVER reference a table or column that is not in the SCHEMA.
- NEVER use placeholder strings like 'start_date', 'end_date', 'value', 'some_value' as literal values.
- For date/timestamp comparisons use real ISO dates: '2024-01-01', '2024-12-31'.
- For numeric comparisons use real numbers: 100, 500, 1000.
- The query must run as-is with NO substitution needed — it is executed directly against PostgreSQL."""


SQL_PASS3_SCHEMA = """Write a correct PostgreSQL SELECT query for this question.

Title: {title}
Category: {sql_category}

Business constraints:
{constraints_str}

SCHEMA — use ONLY these exact table and column names:
{schema_ddl}

RELATIONSHIPS (use these for JOIN ON conditions — if empty, write single-table query):
{relationships_str}

ACTUAL DATA VALUES (use ONLY these values in WHERE/HAVING/IN conditions):
{sample_values_str}

{previous_error_str}RULES:
- Use ONLY tables and columns in SCHEMA. Do NOT invent names.
- If RELATIONSHIPS is empty or has no matching tables, write a single-table query.
- PostgreSQL syntax only. No semicolons in the JSON value.
- CRITICAL: Use ONLY the values shown in ACTUAL DATA VALUES for any WHERE/HAVING/IN filters.
- Do NOT invent filter values — only use values that exist in the data above.
- Avoid HAVING COUNT(*) > N unless N is less than 5 (data has limited rows per group).
- Query runs directly against PostgreSQL with sample data — no substitution happens.

Return ONLY this JSON:
{{
  "reference_query": "SELECT ..."
}}"""


# ─── RAG Reword Prompts (used by generator.py for RAG-based generation) ──────
# These are kept here for backward compatibility with the RAG generator.

from backend.model_app.shared.global_rules import GLOBAL_RULES

# Keywords that indicate domain-specific table names — keep domain if found
_DOMAIN_SPECIFIC_KEYWORDS = {
    "restaurant", "employee", "doctor", "patient", "student", "teacher",
    "hospital", "farmer", "crop", "artist", "supplier", "customer",
    "product", "order", "invoice", "shipment", "warehouse", "store",
    "flight", "passenger", "hotel", "booking", "movie", "actor",
    "author", "book", "publisher", "athlete", "team", "player",
    "department", "salary", "payroll", "vendor", "client",
    "project", "country", "continent", "region", "city", "location",
    "budget", "area", "zone", "district", "territory",
    "account", "transaction", "loan", "bank", "payment",
    "trade", "stock", "portfolio", "fund", "asset",
    "server", "device", "sensor", "log", "event", "session", "user",
    "upgrade", "deployment", "release", "ticket", "issue",
    "species", "sample", "experiment", "measurement", "observation",
    "marine", "organism", "gene", "compound",
}

# Neutral table names — safe to domain-shift
_NEUTRAL_KEYWORDS = {
    "entities", "records", "items", "table", "data", "entry",
    "node", "object", "row", "fact", "dim", "staging",
}


def is_domain_specific(tables: list) -> bool:
    """Return True if any table name contains a domain-specific keyword."""
    combined = " ".join(tables).lower()
    return any(kw in combined for kw in _DOMAIN_SPECIFIC_KEYWORDS)


SQL_REWORD_RULES = GLOBAL_RULES + """
=== SQL REWORD RULES ===
Your task is to rewrite the title, description, and hints of a SQL problem.
Everything else — schemas, sample_data, reference_query, constraints — is LOCKED.

[S1] SCHEMA LOCK — CRITICAL
Do NOT change table names, column names, or data types.
Your title, description, and hints MUST reference the EXACT table names from the schema.
NEVER invent table names that are not in the schema.
NEVER mention columns that are not in the schema.

[S2] QUERY LOCK
The reference_query must remain valid against the original schema.
Your description must require the same SQL logic to solve.

[S3] DOMAIN RULE — READ CAREFULLY
Check the SCHEMA TABLES provided:
- If table names are domain-specific (e.g. Projects, Employees, Patients, Orders):
  KEEP the same domain. Do NOT shift to a different domain.
  Just rewrite the title and description more clearly in the SAME domain.
- If table names are neutral (e.g. entities, records, items, table1):
  SHIFT to a new domain from: e-commerce, logistics, fintech, gaming, social media, education.
  The new domain MUST make sense with the existing column names.

[S4] HINTS RULE — CRITICAL
Each hint must:
- Reference the ACTUAL table names from the schema (e.g. "Look at the Projects table")
- Guide the candidate toward the SQL logic in the reference_query
- NEVER mention tables, columns, or concepts not in the schema

[S5] OUTPUT STRUCTURE
- title: one concise sentence describing what the query finds, using actual table/column names
- description: 3 short paragraphs (under 120 words total), referencing exact table names
- hints: 3 hints that match the schema tables and guide toward the correct SQL approach

[S6] SELF-CHECK before outputting:
- Do all table names in title/description/hints match the schema? YES
- Is description under 120 words? YES
- Do hints reference actual schema tables? YES"""


SQL_REWORD_SCHEMA = """ORIGINAL TITLE:
{title}

ORIGINAL DESCRIPTION:
{description}

ORIGINAL HINTS:
{hints}

SCHEMA TABLES with columns (use these exact names — do NOT invent new table names):
{tables}

REFERENCE QUERY (the correct answer — hints must guide toward this logic):
{reference_query}

DOMAIN INSTRUCTION: {domain_instruction}

Return ONLY this JSON (no markdown, no explanation):
{{"title": "Concise title consistent with the schema tables",
"description": "3 short paragraphs under 120 words, consistent with schema tables: {tables}",
"hints": ["hint 1 — reference actual table/column names and guide toward the SQL technique in the reference query", "hint 2 — reference actual table/column names", "hint 3 — guide toward the specific SQL function or clause used in the reference query (e.g. RANK, PARTITION BY, GROUP BY, JOIN type)"]}}"""
