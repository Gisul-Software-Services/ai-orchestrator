# Requirements Document

## Introduction

This feature adds AI-powered evaluation for DevOps and Cloud candidate submissions, replacing the existing OpenAI-based evaluator in Aaptor with a Qwen-based evaluator running on the local model service. Two new endpoints — `/api/v1/evaluation/devops` and `/api/v1/evaluation/cloud` — accept the full question object and candidate submission, then return a structured score with derived task breakdown and feedback. The evaluator auto-detects mode (terminal/command vs scenario/written) from the submission content. The response contract is identical to Aaptor's existing `ai_feedback` shape so no downstream changes are needed.

---

## Glossary

- **DevOps_Evaluator**: `backend/model_app/evaluation/devops_evaluator.py` — scores DevOps submissions using Qwen.
- **Cloud_Evaluator**: `backend/model_app/evaluation/cloud_evaluator.py` — thin wrapper that calls DevOps_Evaluator.
- **Terminal_Mode**: Submission contains `terminal_history` (list of command+output pairs) and `engine_response`. The LLM evaluates actual execution evidence.
- **Scenario_Mode**: Submission contains a written `answer` with no terminal history. The LLM evaluates the written response.
- **Derived_Tasks**: The LLM derives 3–7 concrete tasks from the question and marks each `completed: true/false` based on the submission evidence.
- **Overall_Score**: `round((completed_tasks / total_tasks) * 100)` — equal weight per task, no manual rubric.
- **Validation_Signals**: The execution engine result passed in the submission — `passed`, `question_score`, `max_score`, `reasons`.
- **TTL_Cache**: `cachetools.TTLCache(maxsize=500, ttl=3600)` keyed on `question_id + submission_hash`.
- **Qwen_LLM**: Local Qwen model via `_llm_chat_coder` from `backend/model_app/evaluation/base.py`.

---

## Requirements

### Requirement 1: DevOps Evaluation Endpoint

**User Story:** As Aaptor, I want to POST a DevOps question and candidate submission to `/api/v1/evaluation/devops` and receive the same `ai_feedback` JSON shape currently returned by the OpenAI evaluator, so that no downstream code changes are needed.

#### Acceptance Criteria

1. THE Evaluation_Router SHALL expose `POST /api/v1/evaluation/devops` accepting a `DevOpsEvalRequest` body.
2. THE response SHALL match the existing Aaptor `ai_feedback` contract exactly — same top-level keys, same nested shapes.
3. THE `DevOpsEvalRequest` SHALL include: `question` (object), `submission` (object), `use_cache` (bool, default `True`).
4. THE `question` object SHALL include: `id`, `title`, `description`, `kind`, `difficulty`, `instructions`, `constraints`, `hints`, `expected_submission_contains`, `expected_exit_code`, `expected_stdout_contains`, `forbidden_stderr_regex`.
5. THE `submission` object SHALL include: `answer` (string), `terminal_history` (list of `{command, output}`), `outputs` (list of strings), `engine_response` (`{exit_code, stdout, stderr}`), `validation_signals` (`{passed, question_score, max_score, reasons}`).
6. THE response SHALL always set `ai_generated: true`.

---

### Requirement 2: Cloud Evaluation Endpoint

**User Story:** As Aaptor, I want to POST a Cloud (AWS) question and submission to `/api/v1/evaluation/cloud` and receive the same `ai_feedback` shape, so that Cloud evaluation works identically to DevOps evaluation.

#### Acceptance Criteria

1. THE Evaluation_Router SHALL expose `POST /api/v1/evaluation/cloud` accepting a `CloudEvalRequest` body with the same fields as `DevOpsEvalRequest`.
2. THE Cloud_Evaluator SHALL delegate directly to DevOps_Evaluator — no separate scoring logic.
3. THE response shape SHALL be identical to the DevOps evaluation response.

---

### Requirement 3: Mode Auto-Detection

**User Story:** As a platform operator, I want the evaluator to automatically detect whether a submission is terminal-based or scenario-based, so that Aaptor does not need to specify the mode explicitly.

#### Acceptance Criteria

1. THE DevOps_Evaluator SHALL detect Terminal_Mode when `terminal_history` is a non-empty list OR `engine_response` is present with a non-null `exit_code`.
2. THE DevOps_Evaluator SHALL detect Scenario_Mode when `terminal_history` is empty or absent AND `answer` is a non-empty string.
3. IF neither condition is met, THE DevOps_Evaluator SHALL default to Scenario_Mode.

---

### Requirement 4: Terminal Mode Evaluation

**User Story:** As a platform operator, I want the LLM to evaluate the candidate's actual terminal commands and outputs against the question requirements, so that the score reflects what the candidate actually executed.

#### Acceptance Criteria

1. WHEN Terminal_Mode is detected, THE DevOps_Evaluator SHALL build a Qwen prompt containing the full `question` object and the full `submission` object (terminal_history, outputs, engine_response, validation_signals).
2. THE prompt SHALL instruct Qwen to derive 3–7 concrete tasks from the question, mark each `completed: true/false` based on execution evidence, and compute `overall_score = round((completed / total) * 100)`.
3. THE prompt SHALL instruct Qwen to use `validation_signals.passed` and `validation_signals.reasons` as supporting evidence but not as the sole basis for task completion.
4. THE prompt SHALL instruct Qwen to return ONLY valid JSON matching the response schema — no markdown, no explanation.

---

### Requirement 5: Scenario Mode Evaluation

**User Story:** As a platform operator, I want the LLM to evaluate the candidate's written answer against the question requirements, so that scenario-based questions are scored on reasoning quality.

#### Acceptance Criteria

1. WHEN Scenario_Mode is detected, THE DevOps_Evaluator SHALL build a Qwen prompt containing the full `question` object and `submission.answer`.
2. THE prompt SHALL instruct Qwen to derive 3–7 concrete tasks from the question, mark each `completed: true/false` based on the written answer, and compute `overall_score = round((completed / total) * 100)`.
3. THE prompt SHALL instruct Qwen to use `instructions`, `hints`, `constraints`, and any `validation_signals` as evidence for task completion.

---

### Requirement 6: Response Schema

**User Story:** As Aaptor, I want every evaluation response to contain all fields in the existing `ai_feedback` contract so that no downstream parsing breaks.

#### Acceptance Criteria

1. THE response SHALL contain all of the following top-level keys:
   `overall_score`, `feedback_summary`, `one_liner`, `code_quality`, `correctness`, `library_usage`, `output_quality`, `task_completion`, `strengths`, `areas_for_improvement`, `suggestions`, `improvement_suggestions`, `deduction_reasons`, `derived_tasks`, `ideal_answer_summary`, `ai_generated`.
2. `code_quality`, `correctness`, `library_usage`, `output_quality` SHALL each be objects with `score` (int 0–100) and `comments` (string).
3. `task_completion` SHALL be an object with `score`, `comments`, `completed` (int), `total` (int), `details` (list of strings).
4. `derived_tasks` SHALL be a list of objects each with `task` (string), `score` (int), `completed` (bool), `evidence` (string), `reasoning` (string).
5. `strengths`, `areas_for_improvement`, `suggestions`, `improvement_suggestions`, `deduction_reasons` SHALL be lists of strings.
6. WHEN the Qwen response omits any field, THE DevOps_Evaluator SHALL substitute a safe default (0, empty string, or empty list) rather than raising an exception.

---

### Requirement 7: Scoring Formula

**User Story:** As a platform operator, I want the overall score to be computed from derived task completion with equal weight per task, matching Aaptor's existing formula.

#### Acceptance Criteria

1. THE DevOps_Evaluator SHALL compute `overall_score = round((completed_tasks / total_tasks) * 100)` where `completed_tasks` is the count of `derived_tasks` with `completed: true`.
2. IF `total_tasks` is zero, THE DevOps_Evaluator SHALL set `overall_score` to 0.
3. THE DevOps_Evaluator SHALL set each `derived_task.score = round(100 / total_tasks)` for completed tasks and 0 for incomplete tasks.
4. THE `task_completion.score` SHALL equal `overall_score`.

---

### Requirement 8: TTL Cache

**User Story:** As a platform operator, I want repeated identical evaluation requests served from cache to avoid redundant LLM calls.

#### Acceptance Criteria

1. THE DevOps_Evaluator SHALL maintain a `TTLCache(maxsize=500, ttl=3600)`.
2. THE cache key SHALL be an MD5 hash of `question.id + serialised(submission)`.
3. WHEN `use_cache` is `True` and a cache entry exists, THE DevOps_Evaluator SHALL return the cached result and call `emit_eval_usage` with `cache_hit=True`.
4. WHEN `use_cache` is `False`, THE DevOps_Evaluator SHALL bypass the cache.

---

### Requirement 9: Deterministic Fallback

**User Story:** As a platform operator, I want a usable response even when Qwen fails, so that a model error never surfaces a 500 to Aaptor.

#### Acceptance Criteria

1. IF Qwen raises an exception or returns unparseable output, THE DevOps_Evaluator SHALL return a fallback response without re-raising.
2. THE fallback SHALL set `overall_score` from `validation_signals.question_score` if available, else 0.
3. THE fallback SHALL set `feedback_summary` to `"Automated scoring applied. Human review recommended."`.
4. THE fallback SHALL set all `score` fields to 0 and all list fields to empty lists.

---

### Requirement 10: Billing Metering

**User Story:** As a platform operator, I want every evaluation call to emit a billing record.

#### Acceptance Criteria

1. WHEN Qwen is called, THE DevOps_Evaluator SHALL call `emit_eval_usage(route="devops_evaluation", latency_ms=<measured>, cache_hit=False)`.
2. WHEN a cache hit occurs, THE DevOps_Evaluator SHALL call `emit_eval_usage(route="devops_evaluation", latency_ms=0, cache_hit=True)`.
3. WHEN Qwen fails, THE DevOps_Evaluator SHALL call `emit_eval_usage(route="devops_evaluation", status="error", error_detail=<str>)`.
4. THE Cloud_Evaluator SHALL use `route="cloud_evaluation"` in all `emit_eval_usage` calls.

---

### Requirement 11: Frontend Proxy Routes

**User Story:** As a frontend developer, I want Next.js proxy routes for both endpoints.

#### Acceptance Criteria

1. THE Frontend SHALL expose `POST /api/admin/evaluate/devops` proxying to `/api/v1/evaluation/devops`.
2. THE Frontend SHALL expose `POST /api/admin/evaluate/cloud` proxying to `/api/v1/evaluation/cloud`.
