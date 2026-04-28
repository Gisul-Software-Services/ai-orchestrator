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

[S1] SCHEMA LOCK
Do NOT change table names, column names, or data types.
Your description and hints MUST reference the exact same table names as provided.

[S2] QUERY LOCK
The reference_query must remain valid against the original schema.
Your description must require the same SQL logic to solve.

[S3] DOMAIN RULE — READ CAREFULLY
Check the SCHEMA TABLES provided:
- If table names are domain-specific (e.g. Employees, restaurants, patients, orders):
  KEEP the same domain. Do NOT shift to a different domain.
  Just rewrite the title and description more clearly in the SAME domain.
- If table names are neutral (e.g. entities, records, items, table1):
  SHIFT to a new domain from: e-commerce, logistics, fintech, gaming, social media, education.
  The new domain MUST make sense with the existing column names.

[S4] OUTPUT STRUCTURE
- title: one concise sentence describing what the query finds
- description: 3 short paragraphs (under 120 words total), referencing exact table names
- hints: rewrite each hint to match the domain context, keep the same SQL logic guidance

[S5] SELF-CHECK
Table names match schema? TRUE. Description consistent with schema? TRUE. Under 120 words? TRUE."""

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
