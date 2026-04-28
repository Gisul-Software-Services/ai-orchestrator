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
The ONLY task is to rewrite the title and description of a SQL problem.
Everything else — schemas, sample_data, reference_query, hints, constraints — is LOCKED.

[S1] SCHEMA LOCK
Do NOT change table names, column names, or data types.
The reworded description MUST reference the exact same table names as provided.

[S2] QUERY LOCK
The reference_query must remain valid against the original schema.
The reworded description must require the same SQL logic to solve.

[S3] DOMAIN SHIFT — MANDATORY
You MUST change the real-world domain to something completely different.
FORBIDDEN domains: agriculture, farming, crops, Texas, insurance, healthcare (unless original is none of these).
REQUIRED: pick a domain from — e-commerce, logistics, fintech, gaming, social media, education, telecom, real estate.
The new domain story MUST make sense with the existing column names.
If you return the same domain as the original, your response is WRONG.

[S4] DESCRIPTION STRUCTURE
3 paragraphs — Context (2-3 sentences), Objective (2-3 sentences), Rules and Constraints (2-3 sentences).
Keep it concise — no more than 150 words total.
Reference the exact table names from the schema in the Objective paragraph.

[S5] SELF-CHECK
Before returning: domain changed? TRUE. Same tables referenced? TRUE. Under 150 words? TRUE."""

SQL_REWORD_SCHEMA = """ORIGINAL TITLE:
{title}

ORIGINAL DESCRIPTION:
{description}

SCHEMA TABLES (you MUST reference these exact table names in your description):
{tables}

FORBIDDEN: Do NOT use the same domain as the original. Pick a completely different real-world context.

Return ONLY this JSON (no markdown, no explanation):
{{"title": "Reworded title in a NEW domain — different story, same SQL logic",
"description": "Concise 3-paragraph description (under 150 words) — NEW domain, exact table names: {tables}"}}"""
