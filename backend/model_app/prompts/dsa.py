from __future__ import annotations


def _is_restricted_path_problem(problem: dict) -> bool:
    title = str(problem.get("title", problem.get("task_id", "")) or "").lower()
    description = str(problem.get("problem_description", problem.get("description", "")) or "").lower()
    return "restricted path" in title or (
        "restricted path" in description and "distancetolastnode" in description
    )


def _build_starter_prompt(problem: dict) -> str:
    """
    Minimal prompt: only asks Qwen for function_signature + starter_code.
    Test cases already extracted from dataset.
    """
    title = problem.get("title", "")
    difficulty = problem.get("difficulty", "Medium")
    topics = ", ".join(problem.get("tags", problem.get("topics", [])))
    description = problem.get("problem_description", problem.get("description", ""))[:400]
    starter_code = problem.get("starter_code", "")
    entry_point = problem.get("entry_point", "")

    fn_hint = ""
    if entry_point:
        fn_hint = entry_point.split(".")[-1].strip() if "." in entry_point else entry_point

    return f"""You are an expert software engineer.

Given this coding problem:
Title: {title}
Difficulty: {difficulty}
Topics: {topics}
Description: {description}

Python starter code:
{starter_code}

Function name: {fn_hint}

Generate ONLY this JSON (no extra text):
{{
  "function_signature": {{
    "name": "{fn_hint}",
    "parameters": [
      {{"name": "paramName1", "type": "List[int]"}},
      {{"name": "paramName2", "type": "int"}}
    ],
    "return_type": "List[int]"
  }},
  "starter_code": {{
    "python":     "def {fn_hint}(param1: List[int], param2: int) -> List[int]:\\n    pass",
    "java":       "class Solution {{\\n    public int[] {fn_hint}(int[] param1, int param2) {{\\n        \\n    }}\\n}}",
    "javascript": "var {fn_hint} = function(param1, param2) {{\\n    \\n}};",
    "typescript": "function {fn_hint}(param1: number[], param2: number): number[] {{\\n    \\n}};",
    "kotlin":     "class Solution {{\\n    fun {fn_hint}(param1: IntArray, param2: Int): IntArray {{\\n        \\n    }}\\n}}",
    "go":         "func {fn_hint}(param1 []int, param2 int) []int {{\\n    \\n}}",
    "rust":       "impl Solution {{\\n    pub fn {fn_hint}(param1: Vec<i32>, param2: i32) -> Vec<i32> {{\\n        \\n    }}\\n}}",
    "cpp":        "#include <bits/stdc++.h>\\nusing namespace std;\\nclass Solution {{\\npublic:\\n    vector<int> {fn_hint}(vector<int>& param1, int param2) {{\\n        \\n    }}\\n}};",
    "csharp":     "public class Solution {{\\n    public int[] {fn_hint}(int[] param1, int param2) {{\\n        \\n    }}\\n}}",
    "c":          "int* {fn_hint}(int* param1, int param1Size, int param2, int* returnSize) {{\\n    \\n}}"
  }}
}}

RULES:
1. function_signature: use EXACT function name from entry point above.
   Extract parameter names + types from the Python starter code.
   Preserve the EXACT same parameter order as the Python starter code.
   Use Python types: List[int], List[str], str, int, bool, float,
   Optional[TreeNode], Optional[ListNode], List[List[int]], etc.
2. starter_code: use EXACT function name for ALL 10 languages.
   Match parameter types correctly for each language.
3. If the canonical parameters are (n, edges), keep them in that exact order everywhere.
   Do NOT swap to (edges, n).
4. Return ONLY valid JSON. No markdown, no explanation.

Generate now:"""


def _build_reword_prompt(problem: dict) -> str:
    title = problem.get("title", problem.get("task_id", ""))
    description = problem.get("problem_description", problem.get("description", ""))[:600]

    restricted_path_rules = ""
    if _is_restricted_path_problem(problem):
        restricted_path_rules = """
- Definition lock for this problem:
  "A restricted path is one where distToN(zi) > distToN(zi+1) for all adjacent nodes."
- Do not introduce new constraints such as thresholds unless explicitly present in the source.
"""

    return f"""You are a technical problem designer.

Below is a coding problem. Your job is to REWORD the problem statement and title ONLY.

STRICT RULES:
- Keep the EXACT same algorithmic logic and solution approach.
- Keep the EXACT same input/output format.
- Change ONLY the real-world story/context (names, domain, scenario wording).
- The reworded version must be clearly different from the original wording.
- Do NOT simplify or make the problem easier or harder.
- Preserve the core semantics of the original title/problem.
{restricted_path_rules}
- Return ONLY valid JSON - no markdown, no extra text.

ORIGINAL TITLE: {title}

ORIGINAL DESCRIPTION:
{description}

Return this exact JSON structure:
{{
  "title": "Reworded title here",
  "description": "Reworded full problem description here - same logic, different story/context"
}}

Generate now:"""




