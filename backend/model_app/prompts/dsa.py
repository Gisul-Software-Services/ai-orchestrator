from __future__ import annotations


def _build_starter_prompt(problem: dict) -> str:
    """
    Minimal prompt — only asks Qwen for function_signature + starter_code.
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
   Use Python types: List[int], List[str], str, int, bool, float,
   Optional[TreeNode], Optional[ListNode], List[List[int]], etc.
2. starter_code: use EXACT function name for ALL 10 languages.
   Match parameter types correctly for each language.
3. Return ONLY valid JSON. No markdown, no explanation.

Generate now:"""


def _build_reword_prompt(problem: dict) -> str:
    title = problem.get("title", problem.get("task_id", ""))
    description = problem.get("problem_description", problem.get("description", ""))[:600]

    return f"""You are a technical problem designer.

Below is a coding problem. Your job is to REWORD the problem statement and title ONLY.

STRICT RULES:
- Keep the EXACT same algorithmic logic and solution approach.
- Keep the EXACT same input/output format.
- Change ONLY the real-world story/context (names, domain, scenario wording).
- The reworded version must be clearly different from the original wording.
- Do NOT simplify or make the problem easier or harder.
- Return ONLY valid JSON — no markdown, no extra text.

ORIGINAL TITLE: {title}

ORIGINAL DESCRIPTION:
{description}

Return this exact JSON structure:
{{
  "title": "Reworded title here",
  "description": "Reworded full problem description here — same logic, different story/context"
}}

Generate now:"""


def _build_aiml_library_prompt(request_data: dict, dataset: dict) -> str:
    topic = request_data.get("topic", "")
    difficulty = request_data.get("difficulty", "Medium")
    concepts = request_data.get("concepts", [])
    concepts_str = ", ".join(concepts) if concepts else "general ML"

    return f"""You are an expert AI/ML assessment designer.

Generate a {difficulty} difficulty AI/ML problem using this REAL dataset.

DATASET INFORMATION:
Name: {dataset.get('name', '')}
Source: {dataset.get('source', '')}
Domain: {dataset.get('domain', '')}
Description: {dataset.get('description', '')}
Features: {dataset.get('features_info', '')}
Target: {dataset.get('target', '')}
Target type: {dataset.get('target_type', '')}
Size: {dataset.get('size', '')}

ASSESSMENT TOPIC: {topic}
CONCEPTS TO TEST: {concepts_str}
DIFFICULTY: {difficulty}

RULES:
- Write a realistic real-world problem statement around THIS specific dataset.
- Tasks must reference the ACTUAL feature names from this dataset.
- Do NOT suggest loading a different dataset.
- Do NOT generate synthetic data.
- expectedApproach must suggest algorithms appropriate for this dataset target type.
- evaluationCriteria must match the target type (classification vs regression metrics).
- ALL fields are REQUIRED.

Return ONLY this JSON:
{{
  "problemStatement": "Detailed real-world problem description grounded in the actual dataset domain",
  "tasks": [
    "Task 1: Data Loading and Exploration — load the {dataset.get('name', '')} dataset using the provided load_code. Examine the actual columns specific to this dataset. Display shape, first 10 rows, check missing values per column, data types, and summary statistics relevant to {topic}.",
    "Task 2: Data Preprocessing — handle any missing values in this specific dataset. Identify which features from {dataset.get('name', '')} need encoding or normalization. Apply appropriate transformations. Split 80/20 train/test.",
    "Task 3: Exploratory Data Analysis — visualize the {dataset.get('target', 'target')} distribution. Plot correlations between features in this {dataset.get('domain', 'domain')} dataset. Create 2-3 meaningful domain-specific plots for {topic}.",
    "Task 4: Model Training — train at least 2 ML models best suited for this {dataset.get('target_type', '')} problem using {dataset.get('name', '')} features. Evaluate with metrics appropriate for this target type.",
    "Task 5: Model Comparison and {dataset.get('domain', 'Domain')} Insights — compare model performance on this specific dataset. Identify the most predictive features. Provide actionable {dataset.get('domain', 'domain')}-specific recommendations for {topic}."
  ],
  "preprocessing_requirements": [
    "Specific step 1 for THIS dataset",
    "Specific step 2 for THIS dataset",
    "Specific step 3 for THIS dataset"
  ],
  "expectedApproach": "2-3 specific ML algorithms suited for this exact dataset with reasoning.",
  "evaluationCriteria": ["metric1", "metric2", "metric3"],
  "difficulty": "{difficulty}",
  "bloomLevel": "Apply"
}}

Generate now:"""

