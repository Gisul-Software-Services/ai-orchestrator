"""
DSA Competency — Question Generation Prompts
=============================================
MODE 1 — RAG REWORD (primary): FAISS match found → reword title + description only
MODE 2 — PURE GENERATION (fallback): no match → generate everything from scratch
"""
from __future__ import annotations

from backend.model_app.shared.global_rules import GLOBAL_RULES

# =============================================================================
# MODE 1 — RAG REWORD (PRIMARY)
# =============================================================================

DSA_REWORD_RULES = GLOBAL_RULES + """
=== DSA REWORD RULES ===
The ONLY task is to change the real-world story of a coding problem.
Nothing else changes.

[R1] ALGORITHM LOCK
The underlying algorithm must be identical to the original.
Never change WHAT the solution computes — only the story that motivates WHY.

[R2] INPUT FORMAT LOCK
The number of parameters must be identical.
The data type of each parameter must be identical.
The order of parameters must be identical — never swap them.

[R3] OUTPUT FORMAT LOCK
The return type must be identical.
Never change what the function returns or its structure.

[R4] CONSTRAINT LOCK
Do NOT add any new constraints.
Do NOT remove any existing constraints.
Do NOT change any numerical limits.
Rephrase the constraints in the new story language only.

[R5] EXAMPLE LOCK
Do NOT change any example inputs or outputs.
Only rephrase the explanation text using the new story context.

[R6] SEMANTIC SELF-CHECK
Before returning output, verify internally:
1. Same algorithm required? TRUE
2. Input format matches exactly? TRUE
3. Output type matches exactly? TRUE
4. No constraints added/removed? TRUE
5. Identical code passes both versions? TRUE"""

DSA_REWORD_SCHEMA = """ORIGINAL TITLE:
{title}

ORIGINAL DESCRIPTION:
{description}
{guardrails}
Return ONLY this JSON:
{{"title": "Reworded title — different real-world story, identical algorithm",
"description": "Reworded full description — different context, identical algorithmic logic, identical input/output format, identical constraints rephrased"}}"""


# =============================================================================
# MODE 2 — PURE GENERATION (FALLBACK)
# =============================================================================

DSA_GENERATION_RULES = GLOBAL_RULES + """
=== DSA GENERATION RULES ===

NARRATIVE REQUIREMENT:
Every question MUST wrap the algorithm in an original real-world scenario.
Draw from unusual fields: astrobotany, deep-sea logistics, quantum routing,
medieval taxation, space station resource allocation, mycological networks.
Parameter names, function name, and test case values must all live in the same world.

DIFFICULTY MAPPING:
EASY   — Basic arrays, string manipulation, O(n) or O(n log n)
MEDIUM — Two pointers, sliding window, BFS/DFS, greedy, O(n log n)
HARD   — Dynamic programming, backtracking, advanced graphs, O(n²) or better

TEST CASE REQUIREMENTS:
Public : exactly 3 (basic, slightly larger, mild edge case)
Hidden : exactly 3 (minimum input, maximum boundary, tricky logical case)
CRITICAL: Every expected output MUST be logically verified. Never guess.

INPUT/OUTPUT FORMAT:
Input  : JSON object with domain-specific parameter names
Output : JSON value — NOT a string representation
Forbidden generic names: nums, arr, k, n, s, t, a, b, list, array"""

DSA_GENERATION_SCHEMA = """Generate a complete DSA coding question:
Topic:      {topic}
Concepts:   {concepts}
Difficulty: {difficulty}
Languages:  {languages}

Return ONLY this JSON:
{{"title": "Scenario-based title",
"difficulty": "{difficulty}",
"description": "3-paragraph description with real-world context following G3",
"examples": [{{"input": "readable input", "output": "readable output", "explanation": "step-by-step"}}],
"constraints": ["1 <= size <= 10^5", "Expected time: O(...)"],
"public_testcases": [
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": false}},
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": false}},
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": false}}
],
"hidden_testcases": [
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": true}},
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": true}},
  {{"input": {{"param1": value}}, "expected_output": value, "is_hidden": true}}
],
"function_signature": {{"name": "camelCaseName", "parameters": [{{"name": "param1", "type": "int[]"}}], "return_type": "int[]"}},
"starter_code": {{"python": "def camelCaseName(param1):\\n    pass"}}
}}"""
