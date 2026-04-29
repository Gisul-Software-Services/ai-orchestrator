"""
Aptor Global Question Generation Rules
=======================================
Prepend GLOBAL_RULES to every competency system prompt.
"""
from __future__ import annotations

GLOBAL_RULES_COMPACT = """=== APTOR GLOBAL RULES ===
[G1] Return ONLY valid JSON. No markdown, no code fences, no preamble.
First character MUST be { and last MUST be }.
Follow the schema exactly. No extra fields.
If unable to generate: {"error": "CANNOT_GENERATE_CLEAN_QUESTION"}

[G2] Formal third-person tone only.
FORBIDDEN: "you", "your", "we", "I", "you should", "you must".
Use: "The candidate must...", "The solution requires...", "The artifact must..."
"""

GLOBAL_RULES = """=== APTOR GLOBAL QUESTION GENERATION RULES ===
These rules apply to every competency and cannot be overridden.

────────────────────────────────────────────────
[G1] OUTPUT FORMAT
────────────────────────────────────────────────
- Return ONLY valid JSON. No markdown, no code fences, no preamble,
  no explanation text outside the JSON.
- The very first character MUST be { and the last MUST be }.
- Follow the competency schema exactly. No extra fields.
- If a valid question cannot be produced, return exactly:
  {"error": "CANNOT_GENERATE_CLEAN_QUESTION"}

────────────────────────────────────────────────
[G2] LANGUAGE AND TONE
────────────────────────────────────────────────
- Use formal, neutral, third-person tone throughout.
- FORBIDDEN words: "you", "your", "we", "I", "you should", "you must",
  "you need to", "you will", "try to".
- Required phrasing:
    "The objective is..."
    "The system requires..."
    "The solution must..."
    "The task involves..."
    "The candidate must..."

────────────────────────────────────────────────
[G3] DESCRIPTION STRUCTURE (3 paragraphs, always)
────────────────────────────────────────────────
Paragraph 1 — CONTEXT
  Real-world scenario. Why this problem exists. Who is affected.
  What the business or technical environment looks like.

Paragraph 2 — OBJECTIVE
  What must be solved, built, designed, or demonstrated.
  The goal stated clearly without procedural instructions.

Paragraph 3 — RULES AND BEHAVIOR
  Constraints, edge case handling, null/missing value behavior,
  tie-breaking logic, ordering rules, special conditions.

────────────────────────────────────────────────
[G4] DIFFICULTY DEFINITIONS
────────────────────────────────────────────────
EASY   — Single concept. Direct solution path. No complex edge cases.
MEDIUM — 2-3 concepts combined. Multi-step reasoning. At least 1 non-trivial edge case.
HARD   — Multiple constraints simultaneously. Optimization or architectural judgment.
         Multiple edge cases, some non-obvious.

────────────────────────────────────────────────
[G5] DETERMINISM
────────────────────────────────────────────────
Every question must define deterministic behavior:
- SORT ORDER: Always specify ascending/descending and tie-breaking column.
- ROUNDING: Specify decimal places and rounding method.
- NULL HANDLING: Specify explicitly — treat null as 0, drop nulls, place nulls last.
- TIE-BREAKING: Define which record wins and why.

────────────────────────────────────────────────
[G6] CONSISTENCY CHECK (run before returning output)
────────────────────────────────────────────────
Before finalizing output, verify:
✓ No ambiguity in the problem statement.
✓ No contradictions between description, examples, and test cases.
✓ Difficulty level matches complexity and edge cases.
✓ Tone is formal and third-person with no forbidden words.
✓ 3-paragraph description structure is followed.
✓ All determinism rules are defined where applicable.
"""
