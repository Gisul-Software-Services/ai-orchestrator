"""
SQL Competency — Question Generation Prompts
============================================
MODE 1 — RAG REWORD (primary): FAISS match found → reword title + description only.
All schemas, sample_data, reference_query, hints, constraints stay from dataset.
"""
from __future__ import annotations

from backend.model_app.shared.global_rules import GLOBAL_RULES

SQL_REWORD_RULES = GLOBAL_RULES + """
=== SQL REWORD RULES ===
Your task is to rewrite the title, description, and hints of a SQL problem into a new domain.
Everything else — schemas, sample_data, reference_query, constraints — is LOCKED.

[S1] SCHEMA LOCK
Do NOT change table names, column names, or data types.
Your description and hints MUST reference the exact same table names as provided.

[S2] QUERY LOCK
The reference_query must remain valid against the original schema.
Your description must require the same SQL logic to solve.

[S3] DOMAIN SHIFT — MANDATORY
You MUST change the real-world domain to something completely different.
FORBIDDEN domains: agriculture, farming, crops, Texas, insurance, healthcare (unless original uses none of these).
REQUIRED: pick from — e-commerce, logistics, fintech, gaming, social media, education, telecom, real estate.
The new domain story MUST make sense with the existing column and table names.
If you return the same domain as the original, your response is WRONG.

[S4] OUTPUT STRUCTURE
- title: one concise sentence in the new domain
- description: 3 short paragraphs (under 120 words total), referencing exact table names
- hints: rewrite each hint to match the new domain context, keep the same SQL logic guidance

[S5] SELF-CHECK
Domain changed? TRUE. Exact table names used? TRUE. Hints updated to new domain? TRUE."""

SQL_REWORD_SCHEMA = """ORIGINAL TITLE:
{title}

ORIGINAL DESCRIPTION:
{description}

ORIGINAL HINTS:
{hints}

SCHEMA TABLES (use these exact names in your output):
{tables}

IMPORTANT: Use a completely different real-world domain. Do NOT use the same domain as the original.

Return ONLY this JSON (no markdown, no explanation):
{{"title": "New title in a different domain",
"description": "3 short paragraphs under 120 words, new domain, references exact table names: {tables}",
"hints": ["hint 1 reworded to new domain", "hint 2 reworded to new domain", "hint 3 reworded to new domain"]}}"""
