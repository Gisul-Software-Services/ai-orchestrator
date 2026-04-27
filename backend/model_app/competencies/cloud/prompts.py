"""
Cloud (AWS) Competency — Question Generation Prompts
=====================================================
Two-pass generation to fit within 1024-token vLLM context:
  Pass 1 — Generate title + description (3 paragraphs)
  Pass 2 — Generate task_steps + validation_hints (code mode)
         — Generate task + evaluation_criteria   (scenario mode)

RAG catalog provides: service, concept, core_idea (AWS API reference).
These are used as topic signal to guide generation — not reworded directly.

MODE: code     — write JSON/YAML/Terraform config for AWS resource (0-5 yrs)
MODE: scenario — architecture/troubleshooting involving AWS services (5+ yrs)
"""
from __future__ import annotations

from backend.model_app.shared.global_rules import GLOBAL_RULES

# ─────────────────────────────────────────────
# SHARED SYSTEM PROMPT (both passes)
# ─────────────────────────────────────────────

CLOUD_SYSTEM = GLOBAL_RULES + """
=== AWS CLOUD COMPETENCY ASSESSMENT RULES ===

CODE MODE: Hands-on AWS resource configuration tasks.
Sandbox constraints (RESTRICTED LINUX SANDBOX, UID 10001):
- No sudo, root, zip, curl, wget, package managers, or script execution.
- No internet access. No real AWS API calls or credentials.
- Allowed tools: mkdir, touch, ls, cp, chmod, cat only.
- Allowed artifacts: JSON policy/config files, YAML CloudFormation templates,
  Terraform .tf files (structure only), directory structures.
- FORBIDDEN: real AWS credentials, CLI commands in the question, solution code,
  Lambda zip files, any task requiring script execution.
- Task steps describe WHAT to create, never HOW to do it.
- Each step produces a deterministically verifiable file or directory artifact.
- Use exact file names, required JSON fields, specific ARN formats, naming rules.

SCENARIO MODE: Production AWS architecture and troubleshooting situations.
- Focus on: multi-service interactions, cost optimization, security posture,
  resilience patterns, incident response, compliance requirements.
- AVOID trivial single-resource tasks.
- The task must require detailed written explanation covering root cause,
  proposed solution, trade-offs, and implementation approach.

DESCRIPTION (always 3 paragraphs, strict third-person, no forbidden words):
  Para 1 — Fictional company scenario: what the company does, what AWS problem
            exists or needs to be built, and the operational/business impact.
  Para 2 — What the artifact or solution must achieve, which AWS services are
            involved, and how the result will be used in production.
  Para 3 — Exact constraints: file names, required JSON/YAML fields, IAM policy
            structure, resource naming conventions, validation conditions.

FORBIDDEN words in output: "you", "your", "we", "I", "you should", "you must".
Use instead: "The candidate must...", "The solution requires...", "The artifact must..."
"""


# ─────────────────────────────────────────────
# PASS 1 — TITLE + DESCRIPTION
# ─────────────────────────────────────────────

CLOUD_PASS1_SCHEMA = """Generate an AWS Cloud {mode} question (PASS 1 — description only).

Parameters: job_role={job_role} | experience={experience_years}yrs | difficulty={difficulty}
AWS Service: {aws_service} | Concepts: {concepts} | Time: {time_limit}min
RAG context: {rag_context}

CRITICAL TONE: Strict third-person only. FORBIDDEN: "you", "your", "we", "I".
Use: "The candidate must...", "The solution requires...", "The artifact must..."

CODE MODE CONSTRAINT: The task involves creating ONLY static configuration files —
JSON policy files, YAML CloudFormation templates, or Terraform .tf files.
NEVER ask for Python scripts, shell scripts, Dockerfiles, or any executable code.
The sandbox has no script execution capability.

Return ONLY this JSON:
{{
  "title": "Concise descriptive title referencing the AWS service and config task",
  "difficulty": "{difficulty}",
  "mode": "{mode}",
  "description": "Three full paragraphs in strict third-person, each starting with its label. EXACTLY this format: 'Para 1: [fictional company scenario — what the company does, what AWS configuration problem exists, operational impact]. Para 2: [what the configuration artifact must achieve, which AWS service is involved, how it will be used — NOT a script]. Para 3: [exact structural constraints — specific file names, required JSON/YAML fields, IAM policy structure, ARN formats, validation conditions].'"
}}"""


# ─────────────────────────────────────────────
# PASS 2 — TASKS (code mode)
# ─────────────────────────────────────────────

CLOUD_PASS2_CODE_SCHEMA = """Given this AWS Cloud CODE question, generate the task steps (PASS 2).

Title: {title}
Description: {description}
Difficulty: {difficulty} | AWS Service: {aws_service}

CRITICAL CONSISTENCY: Task steps MUST use the EXACT same file names, field names,
resource names, ARNs, and values mentioned in the description above.
Do NOT invent names or values not present in the description.

CRITICAL TYPE: Steps must only involve creating JSON/YAML/Terraform CONFIG FILES.
NEVER reference Python scripts, shell scripts, or any executable code.
Step 2 file type must be JSON, YAML, or Terraform — never .py or .sh.

Rules:
- Each step describes WHAT to create or configure, never HOW.
- Each step produces a deterministically verifiable file or directory artifact.
- No AWS CLI commands, no solution code, no vague instructions.

Return ONLY this JSON:
{{
  "task_steps": [
    "Step 1: Create a directory structure at <exact/path> to represent the <AWS resource> configuration.",
    "Step 2: Define a <JSON|YAML|Terraform> file named <exact-filename> containing the following required fields: <field1> set to <exact-value>, <field2> referencing <arn-or-resource-id>.",
    "Step 3: Ensure the <field> is set to <exact-value> and the <policy-element> grants <permission> to <principal>.",
    "Step 4: Verify that <path> contains exactly <N> files matching the naming convention <pattern>."
  ],
  "validation_hints": [
    "File <filename> must exist at <exact/path>.",
    "Field <name> must equal <exact-value>.",
    "The IAM policy must contain an <Effect>/<Action>/<Resource> block matching <specification>.",
    "Directory <path> must contain <N> entries."
  ]
}}"""


# ─────────────────────────────────────────────
# PASS 2 — TASKS (scenario mode)
# ─────────────────────────────────────────────

CLOUD_PASS2_SCENARIO_SCHEMA = """Given this AWS Cloud SCENARIO question, generate the task and evaluation criteria (PASS 2).

Title: {title}
Description: {description}
Difficulty: {difficulty} | AWS Service: {aws_service}

The "task" field must be a REAL engineering question written in third-person,
directly based on the scenario described above. It must NOT be a template or instruction.

Example of a BAD task: "A single open-ended engineering question requiring..."
Example of a GOOD task: "How should the platform team address the Lambda cold start latency described, and what architectural changes to concurrency configuration and VPC placement would reduce p99 latency while staying within the stated cost constraints?"

Return ONLY this JSON:
{{
  "task": "A specific, real engineering question directly referencing the scenario above. Must require explanation of root cause, proposed AWS solution with specific services and configurations, trade-offs, and implementation approach. Written in third-person formal tone.",
  "evaluation_criteria": [
    "Accurately identifies the root cause referencing the specific AWS service behavior.",
    "Proposes a solution using appropriate AWS services that satisfies all stated constraints.",
    "Considers at least two alternative AWS approaches and explains cost/reliability trade-offs.",
    "Addresses security, scalability, or cost implications with specific AWS service references."
  ]
}}"""
