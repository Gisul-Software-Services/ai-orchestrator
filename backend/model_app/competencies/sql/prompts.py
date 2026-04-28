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
The reworded description must reference the exact same tables and columns.

[S2] QUERY LOCK
The reference_query must remain valid against the original schema.
The reworded description must require the same SQL logic to solve.

[S3] DOMAIN SHIFT
Change the real-world domain/story (e.g. agriculture → logistics, healthcare → finance).
The new domain must make sense with the existing column names.

[S4] DESCRIPTION STRUCTURE
Follow G3: 3 paragraphs — Context, Objective, Rules and Behavior.
Keep the same SQL complexity level implied by the original.

[S5] SELF-CHECK
Before returning: same tables required? TRUE. Same query solves it? TRUE."""

SQL_REWORD_SCHEMA = """ORIGINAL TITLE:
{title}

ORIGINAL DESCRIPTION:
{description}

SCHEMA TABLES (you MUST reference these exact table names in the description):
{tables}

Return ONLY this JSON:
{{"title": "Reworded title — different real-world story, same SQL logic",
"description": "Reworded 3-paragraph description — different domain context, must reference the exact table names above"}}"""
