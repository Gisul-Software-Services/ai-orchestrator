

def build_topics_prompt(request_data):
    return f"""Generate {request_data['num_topics']} assessment topics for {request_data['job_designation']}.
Skills: {', '.join(request_data['skills'])}
Experience: {request_data['experience_min']}-{request_data['experience_max']} years

RULES:
- "label" must be a SHORT topic name only (2-6 words). NOT a sentence or question.
  GOOD: "Python List Slicing", "SQL Window Functions", "React useEffect Hook"
  BAD: "Understanding how Python handles list slicing operations"
- Mix difficulty: ~30% Easy, ~50% Medium, ~20% Hard based on experience level.
- questionType must match the topic — use AIML only for ML/data science topics.
- canUseJudge0 is true only for Coding/SQL topics.

Return ONLY JSON:
{{"topics": [{{"label": "Short Topic Name", "questionType": "MCQ|Subjective|Coding|SQL|AIML|PseudoCode", "difficulty": "Easy|Medium|Hard", "canUseJudge0": true|false}}]}}"""


def build_subjective_prompt(request_data):
    return f"""
You are a strict assessment generator.

Generate ONE {request_data['difficulty']} subjective question about {request_data['topic']}.

STRICT RULES:
- Return ONLY valid JSON.
- No markdown.
- No extra explanation outside JSON.
- All fields REQUIRED.
- expectedAnswer must be detailed, at least 3-4 sentences.
- gradingCriteria: EXACTLY 4 specific, measurable criteria — NOT generic ones.
  BAD: "Correctness", "Clarity", "Understanding"
  GOOD: "Correctly explains the difference between X and Y with an example",
        "Mentions at least 2 real-world use cases", "Addresses edge case Z",
        "Uses accurate technical terminology"

MANDATORY JSON FORMAT:
{{
  "question": "Complete question text",
  "expectedAnswer": "Detailed answer explanation covering all key points",
  "gradingCriteria": [
    "Specific criterion 1 tied to the answer content",
    "Specific criterion 2 tied to the answer content",
    "Specific criterion 3 tied to the answer content",
    "Specific criterion 4 tied to the answer content"
  ],
  "difficulty": "{request_data['difficulty']}",
  "bloomLevel": "Apply"
}}

Generate now:
"""



def build_coding_prompt(request_data):
    difficulty = request_data["difficulty"]
    topic = request_data["topic"]
    language = request_data["language"]
    job_role = request_data.get("job_role", "Software Engineer")
    exp_years = request_data.get("experience_years", "3-5")

    difficulty_guidance = {
        "Easy": (
            "suitable for a junior developer screening. "
            "Focus on clean implementation of a single well-known algorithm or data structure. "
            "The problem should be solvable in 20-30 minutes."
        ),
        "Medium": (
            "suitable for a mid-level engineer technical interview. "
            "Require combining 2 concepts (e.g. hash map + sliding window, BFS + memoisation). "
            "Must have a naive O(n^2) solution and an optimal solution that the candidate should discover. "
            "Solvable in 30-45 minutes by a competent engineer."
        ),
        "Hard": (
            "suitable for a senior/staff engineer interview at a top tech company. "
            "Require deep algorithmic thinking: dynamic programming, graph algorithms, segment trees, "
            "or complex system-level design within a function. "
            "Must have multiple sub-problems or edge cases that trip up average candidates. "
            "Solvable in 45-60 minutes by a strong engineer."
        ),
    }.get(difficulty, "suitable for a mid-level engineer.")

    lang_starter = {
        "Python": "def solution():\n    # your code here\n    pass",
        "JavaScript": "function solution() {\n    // your code here\n}",
        "Java": "public class Solution {\n    public static void main(String[] args) {\n        // your code here\n    }\n}",
        "C++": "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // your code here\n    return 0;\n}",
        "Go": "package main\n\nimport \"fmt\"\n\nfunc solution() {\n    // your code here\n}",
        "TypeScript": "function solution(): void {\n    // your code here\n}",
    }.get(language, "// your code here")

    return f"""You are a senior engineering interviewer at a top-tier technology company.

Your task: Write ONE production-grade {difficulty} coding problem for a {job_role} with {exp_years} years of experience.
Topic area: {topic}
Language: {language}
Difficulty profile: {difficulty_guidance}

QUALITY REQUIREMENTS — every item below is MANDATORY:
1. problemStatement: Must describe a REAL-WORLD scenario (not abstract). Use concrete domain context
   such as e-commerce order processing, a ride-sharing dispatch system, log analysis pipeline,
   financial transaction deduplication, etc. The problem must feel like something from production.
2. The problem must test ALGORITHMIC THINKING, not syntax knowledge.
3. constraints: Must include realistic upper bounds (e.g. 1 <= n <= 10^6, values up to 10^9).
   At least 4 constraints. One constraint must push the candidate toward an optimal solution
   (e.g. "must run in O(n log n) or better", "memory limited to O(k)").
4. examples: At least 2 examples. Each must include a non-trivial input, the correct output,
   and a step-by-step explanation showing WHY the output is correct.
5. testCases: At least 5 test cases total.
   - 2 visible (isHidden: false): one simple, one moderate
   - 3 hidden (isHidden: true): must include edge cases:
     empty input, single element, maximum constraint values, duplicate values,
     negative numbers (if applicable), already-sorted input, etc.
6. starterCode: Must include the correct function signature with typed parameters.
   Include a brief docstring describing what the function should do.
7. The expectedComplexity field must state both time AND space complexity of the optimal solution.

STRICT OUTPUT RULES:
- Return ONLY valid JSON — no markdown fences, no explanation outside JSON.
- All string values must be plain strings (no nested objects).
- Newlines inside strings must use \n escape.
- constraints, examples, testCases must be JSON arrays.

EXACT JSON STRUCTURE:
{{
  "problemStatement": "Detailed real-world problem description as a single string",
  "inputFormat": "Precise input format description",
  "outputFormat": "Precise output format description",
  "constraints": [
    "1 <= n <= 10^6",
    "0 <= values[i] <= 10^9",
    "Solution must run in O(n log n) or better",
    "Memory usage must be O(n)"
  ],
  "examples": [
    {{
      "input": "concrete example input",
      "output": "exact expected output",
      "explanation": "Step-by-step walkthrough of why this output is correct"
    }},
    {{
      "input": "second more complex example",
      "output": "expected output",
      "explanation": "Detailed explanation"
    }}
  ],
  "testCases": [
    {{"input": "simple test", "expectedOutput": "output", "isHidden": false}},
    {{"input": "moderate test", "expectedOutput": "output", "isHidden": false}},
    {{"input": "edge case: empty", "expectedOutput": "output", "isHidden": true}},
    {{"input": "edge case: max constraint", "expectedOutput": "output", "isHidden": true}},
    {{"input": "edge case: duplicates or boundary", "expectedOutput": "output", "isHidden": true}}
  ],
  "starterCode": "{lang_starter}",
  "difficulty": "{difficulty}",
  "expectedComplexity": "Time: O(...) | Space: O(...)",
  "hints": [
    "First hint pointing toward the right approach without giving it away",
    "Second hint for candidates who are stuck"
  ]
}}

Generate the problem now:"""


def build_sql_prompt(request_data):
    difficulty = request_data["difficulty"]
    topic = request_data["topic"]
    db_type = request_data.get("database_type", "PostgreSQL")
    job_role = request_data.get("job_role", "Software Engineer")
    exp_years = request_data.get("experience_years", "3-5")

    difficulty_guidance = {
        "Easy": (
            "Test basic SELECT, WHERE, ORDER BY, GROUP BY, and simple JOINs. "
            "Schema should have 2-3 tables with obvious relationships. "
            "Solvable by a junior developer in 10-15 minutes."
        ),
        "Medium": (
            "Test multi-table JOINs across at least 3 tables, CTEs, and window functions "
            "(ROW_NUMBER, RANK, LAG/LEAD). Include a subtle requirement like ranking per group "
            "or finding the top-N per category. Solvable by a mid-level engineer in 20-30 minutes."
        ),
        "Hard": (
            "Test recursive CTEs, complex window functions (running totals, moving averages), "
            "or self-joins on hierarchical data. The naive correlated-subquery solution must be "
            "clearly worse. Solvable by a senior engineer in 30-45 minutes."
        ),
    }.get(difficulty, "Test intermediate SQL skills.")

    sql_concepts = {
        "Easy": "Basic JOINs, GROUP BY, ORDER BY, simple aggregations",
        "Medium": "CTEs, window functions (ROW_NUMBER/RANK/LAG), multi-table JOINs, HAVING",
        "Hard": "Recursive CTEs, advanced window functions, self-joins, complex aggregations",
    }.get(difficulty, "Intermediate SQL")

    return f"""You are a senior database engineer writing a technical interview question.

Task: Write ONE {difficulty} SQL problem for a {job_role} with {exp_years} years experience.
Topic: {topic}
Database: {db_type}
Difficulty: {difficulty_guidance}
Concepts: {sql_concepts}

RULES:
1. problemStatement: Real business scenario (e-commerce, SaaS, logistics, finance, HR). One paragraph, single string.
2. schema: 2-3 tables, realistic column names and types, foreign key relationships. Columns only — NO sample_data rows.
3. expectedQuery: The correct {db_type} solution. CRITICAL — write the entire SQL on ONE single line using spaces between clauses. Do NOT use real newlines inside the query string. Example: "SELECT u.name, COUNT(o.id) AS total FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name ORDER BY total DESC"
4. explanation: Plain English walkthrough of the query — why each JOIN type, what each clause does. Single string.
5. alternativeApproach: One sentence describing a worse approach and why it is slower or incorrect.
6. concepts_tested: List of SQL concepts this question tests.

CRITICAL JSON RULES:
- Return ONLY a valid JSON object. No markdown. No text before or after the JSON.
- Every value must be a plain string or array — no nested objects except schema.tables.
- NO real newlines inside any string value. Use a space instead.
- NO tab characters inside any string value.
- NO control characters of any kind inside string values.

JSON FORMAT:
{{
  "problemStatement": "single string describing the real business problem",
  "schema": {{
    "database": "{db_type}",
    "tables": [
      {{
        "name": "users",
        "columns": [
          {{"name": "id", "type": "SERIAL", "primary_key": true}},
          {{"name": "email", "type": "VARCHAR(100)", "nullable": false}},
          {{"name": "created_at", "type": "TIMESTAMP"}}
        ]
      }},
      {{
        "name": "orders",
        "columns": [
          {{"name": "id", "type": "SERIAL", "primary_key": true}},
          {{"name": "user_id", "type": "INTEGER", "foreign_key": "users.id"}},
          {{"name": "amount", "type": "DECIMAL(10,2)"}},
          {{"name": "status", "type": "VARCHAR(20)"}}
        ]
      }}
    ]
  }},
  "expectedQuery": "SELECT u.email, SUM(o.amount) AS total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.email ORDER BY total DESC LIMIT 10",
  "explanation": "We join users to orders on user_id to combine user info with order data. We filter only completed orders using WHERE. GROUP BY aggregates totals per user. ORDER BY DESC with LIMIT 10 returns the top spenders.",
  "alternativeApproach": "A correlated subquery in SELECT would compute the sum per user but runs once per row making it O(n*m) versus the JOIN approach which is O(n log n).",
  "difficulty": "{difficulty}",
  "concepts_tested": ["{sql_concepts}"]
}}

Generate now:"""


