"""
SQL Competency — Question Generation Prompts
============================================
MODE 1 — RAG REWORD (primary): FAISS match found → reword title/description/hints.
All schemas, sample_data, reference_query, constraints stay LOCKED.
"""
from __future__ import annotations

from backend.model_app.shared.global_rules import GLOBAL_RULES

# Keywords that indicate domain-specific table names — keep domain if found
_DOMAIN_SPECIFIC_KEYWORDS = {
    "restaurant", "employee", "doctor", "patient", "student", "teacher",
    "hospital", "farmer", "crop", "artist", "supplier", "customer",
    "product", "order", "invoice", "shipment", "warehouse", "store",
    "flight", "passenger", "hotel", "booking", "movie", "actor",
    "author", "book", "publisher", "athlete", "team", "player",
    "department", "salary", "payroll", "vendor", "client",
    # geography / project domains
    "project", "country", "continent", "region", "city", "location",
    "budget", "area", "zone", "district", "territory",
    # finance / banking
    "account", "transaction", "loan", "bank", "payment", "invoice",
    "trade", "stock", "portfolio", "fund", "asset",
    # tech / infra
    "server", "device", "sensor", "log", "event", "session", "user",
    "upgrade", "deployment", "release", "ticket", "issue",
    # science / research
    "species", "sample", "experiment", "measurement", "observation",
    "marine", "organism", "gene", "compound",
}

# Neutral table names — safe to domain-shift
_NEUTRAL_KEYWORDS = {
    "entities", "records", "items", "table", "data", "entry",
    "node", "object", "row", "fact", "dim", "staging",
}


def is_domain_specific(tables: list[str]) -> bool:
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

SCHEMA TABLES (use these exact names — do NOT invent new table names):
{tables}

DOMAIN INSTRUCTION: {domain_instruction}

Return ONLY this JSON (no markdown, no explanation):
{{"title": "Concise title consistent with the schema tables",
"description": "3 short paragraphs under 120 words, consistent with schema tables: {tables}",
"hints": ["hint 1 consistent with schema", "hint 2 consistent with schema", "hint 3 consistent with schema"]}}"""
