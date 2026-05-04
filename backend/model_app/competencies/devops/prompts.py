"""
DevOps / Cloud Competency — Question Generation Prompts
========================================================
Two-pass generation to fit within 1024-token vLLM context:
  Pass 1 — Generate title + description (3 paragraphs)
  Pass 2 — Generate task_steps/task + validation using Pass 1 output

MODE: code     — hands-on file/config tasks for sandbox (0-5 yrs)
MODE: scenario — architecture reasoning and troubleshooting (5+ yrs)
"""
from __future__ import annotations

from backend.model_app.shared.global_rules import GLOBAL_RULES

# ─────────────────────────────────────────────
# SHARED SYSTEM PROMPT (both passes)
# ─────────────────────────────────────────────

DEVOPS_SYSTEM = GLOBAL_RULES + """
=== DEVOPS / CLOUD ASSESSMENT RULES ===

CODE MODE: Hands-on file/config tasks. Sandbox constraints:
- No sudo, root, zip, curl, wget, package managers, or scripts.
- Allowed: mkdir, touch, ls, cp, chmod, cat only.
- Artifacts: JSON/YAML configs, Terraform .tf files, directory structures.
- Never include commands or solution code in the question.

SCENARIO MODE: Production cloud situations requiring architecture reasoning.
- Focus on troubleshooting, resilience, multi-service interactions.
- The task must require detailed written explanation of reasoning.
- Never include trivial single-resource tasks.

DESCRIPTION (always 3 paragraphs, third-person, no forbidden words):
  Para 1 — Fictional company scenario: what they do, what broke/needs building.
  Para 2 — What the artifact/solution must achieve and why it matters.
  Para 3 — Exact constraints: file names, required fields, naming rules, validation."""


# ─────────────────────────────────────────────
# PASS 1 — TITLE + DESCRIPTION
# ─────────────────────────────────────────────

DEVOPS_PASS1_SCHEMA = """Generate a DevOps {mode} question (PASS 1 — description only).

Parameters: job_role={job_role} | experience={experience_years}yrs | difficulty={difficulty}
Focus: {focus_area} | Topics: {topics} | RAG hint: {rag_context}

CRITICAL TONE RULE: Strict third-person only. FORBIDDEN words: "you", "your", "we", "I".
Use instead: "The candidate must...", "The system requires...", "The solution must...", "The artifact must..."

CODE MODE CONSTRAINT: Artifacts must be ONLY static config files — JSON, YAML, or Terraform .tf.
NEVER ask for Dockerfiles, Python scripts, shell scripts, or any executable code.

Return ONLY this JSON:
{{
  "title": "Concise descriptive title, no solution hints",
  "difficulty": "{difficulty}",
  "mode": "{mode}",
  "description": "Three full paragraphs in strict third-person, each starting with its label. EXACTLY this format: 'Para 1: [fictional company scenario — what the company does, what broke or needs building, operational impact]. Para 2: [what the artifact or solution must achieve and how it will be used — no forbidden words]. Para 3: [exact structural constraints — specific file names, required fields, naming conventions, validation conditions].'"
}}"""


# ─────────────────────────────────────────────
# PASS 2 — TASKS (code mode)
# ─────────────────────────────────────────────

DEVOPS_PASS2_CODE_SCHEMA = """Given this DevOps CODE question, generate the task steps (PASS 2).

Title: {title}
Description: {description}
Difficulty: {difficulty} | Focus: {focus_area}

CRITICAL CONSISTENCY: Task steps MUST use the EXACT same file names, paths,
field names, and values mentioned in the description above.
Do NOT invent names or values not present in the description.

CRITICAL: Do NOT include solution values in task steps.
BAD: "Set command to ['sshd', '-D']" — this reveals the solution.
GOOD: "Ensure the command field is configured to start the SSH daemon as specified."

Rules:
- Each step describes WHAT to create, never HOW or WHAT VALUE to use.
- Each step produces a deterministically verifiable artifact.
- No solution code, no exact command values, no vague instructions.

Return ONLY this JSON:
{{
  "task_steps": [
    "Step 1: Create directory structure at <exact/path> for <purpose>.",
    "Step 2: Define a <JSON|YAML|Terraform> file named <exact-filename> containing fields: <field1>, <field2>, <field3>.",
    "Step 3: Ensure <field> references <resource-from-description> and <other-field> is configured for <purpose>.",
    "Step 4: Verify <path> contains exactly <N> files matching the pattern <naming-convention>."
  ],
  "validation_hints": [
    "File <filename> must exist at <exact/path>.",
    "Field <name> must equal <exact-value-from-description>.",
    "Directory <path> must contain <N> entries named <pattern>."
  ]
}}"""


# ─────────────────────────────────────────────
# PASS 2 — TASKS (scenario mode)
# ─────────────────────────────────────────────

DEVOPS_PASS2_SCENARIO_SCHEMA = """Given this DevOps SCENARIO question, generate the task and evaluation criteria (PASS 2).

Title: {title}
Description: {description}
Difficulty: {difficulty} | Focus: {focus_area}

The "task" field must be a REAL engineering question written in third-person,
directly based on the scenario described above. It must NOT be a template or instruction.

Example of a BAD task: "A single open-ended engineering question requiring..."
Example of a GOOD task: "How should the infrastructure team diagnose the root cause of the deployment failures described, and what architectural changes would prevent recurrence while maintaining the stated availability requirements?"

Return ONLY this JSON:
{{
  "task": "A specific, real engineering question directly referencing the scenario above. Must require explanation of root cause, proposed solution with trade-offs, and implementation approach. Written in third-person formal tone.",
  "evaluation_criteria": [
    "Accurately identifies the root cause of the described problem.",
    "Proposes a solution that satisfies all stated constraints.",
    "Considers at least two alternative approaches and explains trade-offs.",
    "Addresses reliability, scalability, or cost implications explicitly."
  ]
}}"""
