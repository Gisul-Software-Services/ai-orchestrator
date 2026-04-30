# Requirements Document

## Introduction

The SQL AI Evaluation feature adds a `/api/v1/evaluation/sql` endpoint to the model service that produces structured AI-powered scoring and feedback for candidate SQL query submissions. It follows the exact same pattern as the existing DSA and AIML evaluators (`dsa_evaluator.py`, `aiml_evaluator.py`) — using the Qwen coder model via `_llm_chat_coder`, TTL caching via `cachetools.TTLCache`, safe JSON parsing via `safe_parse`, and billing via `emit_eval_usage`.

The external execution engine (on the assessment platform) already runs the candidate's SQL and sends the execution result to our service. Our service receives that result plus question context, calls Qwen to generate a score and detailed feedback, and returns the structured `ai_feedback` JSON that the platform stores on the submission document.

## System Flow

```
Candidate submits SQL query
        ↓
Execution Engine (external, assessment platform)
  - Runs candidate SQL against real DB
  - Compares result to expected output
  - Produces: passed (bool), user_output, expected_output, error
        ↓
POST /api/v1/evaluation/sql  (our model service)
  - Receives execution result + question context
  - Checks TTL cache (keyed on question_id + user_query hash)
  - Calls Qwen coder model to generate AI score + feedback
  - Enforces Score_Floor / Score_Cap as hard post-processing
  - Returns structured ai_feedback JSON
        ↓
Platform stores ai_feedback on submission document
```

## Glossary

- **Execution_Result**: Output from the external execution engine — `passed` (bool), `user_output` (JSON string), `expected_output` (JSON string), `error` (string or null).
- **Candidate_Query**: The SQL string submitted by the candidate.
- **Reference_Query**: The correct SQL answer stored on the question (used in Qwen prompt, never returned to candidate).
- **AI_Feedback**: The structured scoring and feedback object produced by Qwen and returned by this service.
- **Criteria_Scores**: Per-criterion breakdown — correctness (40%), efficiency (25%), best_practices (15%), edge_cases (10%), alternative_solutions (10%).
- **Score_Floor**: When `passed=true`, overall score must be ≥ `max_marks × 0.8`.
- **Score_Cap**: When `passed=false`, overall score must be ≤ `max_marks × 0.5`.
- **Max_Marks**: Maximum score for the question, passed in the request body.
- **TTL Cache**: In-memory `cachetools.TTLCache` keyed on `(question_id, md5(user_query))`, TTL = 3600s, maxsize = 500.

---

## Requirements

### Requirement 1: SQL Evaluation Endpoint

**User Story:** As the assessment platform, I want to POST the execution result and question context to the model service and receive structured AI feedback, so that candidate SQL submissions are automatically scored.

#### Acceptance Criteria

1. THE service SHALL expose a POST endpoint at `/api/v1/evaluation/sql` registered on the existing `evaluation` router in `backend/model_app/api/routes/evaluation.py`.
2. THE endpoint SHALL accept a JSON body with the following fields:
   - `question_id` (string, required)
   - `question_description` (string, required)
   - `user_query` (string, required) — candidate's submitted SQL
   - `reference_query` (string, required) — correct SQL answer
   - `max_marks` (float, required) — maximum score for this question
   - `schemas` (object, required) — table definitions from the question
   - `test_result` (object, required) — execution result from the execution engine:
     - `passed` (boolean)
     - `user_output` (string) — JSON string of candidate's result rows
     - `expected_output` (string) — JSON string of expected result rows
     - `error` (string or null)
   - `order_sensitive` (boolean, optional, default false)
   - `difficulty` (string, optional, default "medium") — easy / medium / hard
   - `section` (string, optional, default "")
   - `use_cache` (boolean, optional, default true)
3. IF any required field is missing, THE service SHALL return HTTP 422 with a descriptive validation error.
4. THE service SHALL return HTTP 200 for all successfully processed requests regardless of pass/fail verdict.
5. IF an internal error occurs, THE service SHALL return HTTP 500 with a `detail` field.

---

### Requirement 2: TTL Caching

**User Story:** As a platform engineer, I want identical evaluation requests to return cached results, so that repeated submissions of the same query don't consume model resources.

#### Acceptance Criteria

1. THE evaluator SHALL use a `cachetools.TTLCache(maxsize=500, ttl=3600)` — matching the DSA and AIML evaluator pattern.
2. THE cache key SHALL be `md5(f"{question_id}:{user_query}:{passed}")` — including `passed` to avoid stale results if execution changes.
3. WHEN `use_cache=true` and a cache hit is found, THE service SHALL return the cached result and call `emit_eval_usage` with `cache_hit=True`.
4. WHEN `use_cache=false`, THE service SHALL bypass the cache and always call Qwen.
5. WHEN a new result is computed, THE service SHALL store it in the cache before returning.

---

### Requirement 3: Qwen Prompt Construction

**User Story:** As a platform engineer, I want the Qwen prompt to include all relevant context so that the AI produces accurate, SQL-specific feedback.

#### Acceptance Criteria

1. THE system prompt SHALL instruct Qwen to return ONLY minified JSON with no markdown, no code fences, no extra keys — matching the AIML evaluator pattern.
2. THE system prompt SHALL define the exact output schema (see Requirement 5).
3. THE system prompt SHALL specify SQL-specific evaluation criteria:
   - Correctness (40%): does the result match expected output
   - Efficiency (25%): index usage, full table scans, window functions vs subqueries
   - Best Practices (15%): aliases, formatting, readability, SQL conventions
   - Edge Cases (10%): NULL handling, empty results, boundary conditions
   - Alternative Solutions (10%): better approaches (CTEs, window functions, etc.)
4. THE system prompt SHALL explicitly forbid O(n) notation — use SQL-specific terms only (e.g. "full table scan", "index seek", "correlated subquery overhead").
5. THE system prompt SHALL state: if `passed=true` → minimum score is 80% of max_marks; if `passed=false` → maximum score is 50% of max_marks.
6. THE user prompt SHALL include:
   - `question_description` (truncated to 1000 chars)
   - `difficulty`
   - `schemas` (table names and column definitions)
   - `user_query` (candidate's SQL)
   - `reference_query` — included for Qwen context only, never returned to candidate
   - `order_sensitive`
   - `test_result.passed` (bool)
   - `test_result.user_output` (truncated to 500 chars)
   - `test_result.expected_output` (truncated to 500 chars)
   - `test_result.error` (if any, truncated to 300 chars)
   - `max_marks`
7. THE user prompt SHALL NOT include the full `sql_expected_output` dataset — only the truncated `test_result.expected_output` string.

---

### Requirement 4: Score Enforcement

**User Story:** As the assessment platform, I want score floors and caps enforced deterministically, so that passed queries always score at least 80% and failed queries never exceed 50%.

#### Acceptance Criteria

1. AFTER Qwen returns a score, THE service SHALL apply Score_Floor and Score_Cap as a hard post-processing step — not relying on Qwen to self-enforce.
2. WHEN `test_result.passed=true`, THE `score` SHALL be clamped to `max(score, max_marks * 0.8)`.
3. WHEN `test_result.passed=false`, THE `score` SHALL be clamped to `min(score, max_marks * 0.5)`.
4. THE `percentage` SHALL be recomputed as `round((score / max_marks) * 100, 2)` after clamping.
5. ALL `criteria_scores` individual scores SHALL be non-negative and their weighted sum SHALL equal `score` after clamping — redistribute proportionally if needed.

---

### Requirement 5: AI_Feedback Response Schema

**User Story:** As the assessment platform, I want the AI feedback to follow the exact existing contract schema, so that it can be stored and displayed without transformation.

#### Acceptance Criteria

1. THE service SHALL return a JSON response matching this exact schema:
```json
{
  "question_id": "string",
  "section": "string",
  "question_type": "SQL",
  "score": 0.0,
  "max_marks": 0.0,
  "percentage": 0.0,
  "criteria_scores": {
    "correctness":           { "score": 0.0, "weight": 0.40, "feedback": "string" },
    "efficiency":            { "score": 0.0, "weight": 0.25, "feedback": "string" },
    "best_practices":        { "score": 0.0, "weight": 0.15, "feedback": "string" },
    "edge_cases":            { "score": 0.0, "weight": 0.10, "feedback": "string" },
    "alternative_solutions": { "score": 0.0, "weight": 0.10, "feedback": "string" }
  },
  "feedback": {
    "summary": "string",
    "strengths": ["string"],
    "weaknesses": ["string"],
    "detailed_analysis": "string",
    "suggestions": ["string"]
  },
  "answer_log": {
    "submitted_answer": "string",
    "expected_answer": "",
    "key_points_covered": ["string"],
    "key_points_missed": ["string"],
    "incorrect_points": [],
    "partial_credit_reasoning": "string"
  },
  "areas_of_improvement": [
    {
      "skill": "string",
      "current_level": "string",
      "gap_analysis": "string",
      "priority": "string",
      "improvement_suggestions": [
        {
          "suggestion": "string",
          "resources": ["string"],
          "practice_exercises": ["string"],
          "estimated_time": "string"
        }
      ]
    }
  ],
  "benchmarking": {
    "compared_to_peers": "string",
    "percentile": 0.0,
    "industry_standard": "string"
  },
  "insights": {
    "approach_quality": "string",
    "edge_case_handling": "string",
    "alternative_solutions": ["string"]
  },
  "flags": {
    "plagiarism_risk": "Low",
    "ai_generated_risk": "Low",
    "incomplete_answer": false,
    "requires_human_review": false,
    "confidence_level": 0.0
  },
  "evaluation_version": "2.1.0",
  "ai_generated": true
}
```
2. THE `answer_log.expected_answer` SHALL always be an empty string — the reference query is never exposed to the candidate.
3. THE `answer_log.submitted_answer` SHALL contain the candidate's `user_query`.
4. THE `flags.incomplete_answer` SHALL be `true` when `user_query` is empty or whitespace only.
5. THE `flags.requires_human_review` SHALL be `true` when fallback scoring is applied.
6. THE `ai_generated` field SHALL always be `true`.

---

### Requirement 6: Fallback Scoring

**User Story:** As the assessment platform, I want the evaluation to always return a valid score even if Qwen fails, so that submissions are never left ungraded.

#### Acceptance Criteria

1. IF Qwen raises an exception or `safe_parse` returns `parse_error=True`, THE service SHALL apply deterministic fallback scoring — matching the DSA evaluator fallback pattern.
2. WHEN `test_result.passed=true` and fallback is applied, THE `score` SHALL be `max_marks * 0.8`.
3. WHEN `test_result.passed=false` and fallback is applied, THE `score` SHALL be `max_marks * 0.3`.
4. WHEN fallback is applied, THE `flags.requires_human_review` SHALL be `true`.
5. WHEN fallback is applied, THE `feedback.summary` SHALL be `"Automated scoring applied. Human review recommended."`.
6. WHEN fallback is applied, THE service SHALL log a warning with `logger.warning`.
7. WHEN fallback is applied, THE service SHALL call `emit_eval_usage` with `status="error"` and the exception detail.

---

### Requirement 7: Empty / Invalid Submission Handling

**User Story:** As the assessment platform, I want empty or trivially invalid submissions to be handled immediately without calling Qwen, so that model resources are not wasted.

#### Acceptance Criteria

1. IF `user_query` is empty or contains only whitespace, THE service SHALL return a zero-score response immediately without calling Qwen.
2. WHEN `user_query` is empty, THE `flags.incomplete_answer` SHALL be `true` and `score` SHALL be `0`.
3. IF `user_query` is shorter than 10 characters (excluding whitespace), THE service SHALL treat it as an empty submission.

---

### Requirement 8: Billing and Usage Metering

**User Story:** As a platform engineer, I want SQL evaluation usage to be tracked in billing, so that model consumption is accurately metered.

#### Acceptance Criteria

1. THE service SHALL call `emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=..., cache_hit=...)` on every request — matching the DSA and AIML evaluator pattern.
2. THE service SHALL call `bind_usage_meta_from_request(http_request)` at the route level to populate `usage_meta`.
3. WHEN a cache hit occurs, THE service SHALL call `emit_eval_usage` with `cache_hit=True` and `latency_ms=0`.
4. WHEN Qwen is called, THE service SHALL measure wall-clock latency from before the `_llm_chat_coder` call to after, and pass it as `latency_ms`.
5. WHEN an error occurs, THE service SHALL call `emit_eval_usage` with `status="error"` and `error_detail=str(exception)`.

---

### Requirement 9: Response Normalization

**User Story:** As a platform engineer, I want all Qwen output to be normalized to the contract schema, so that malformed or partial model responses never break the platform.

#### Acceptance Criteria

1. THE service SHALL implement a `_normalize_product(raw: dict) -> dict` function — matching the AIML evaluator pattern.
2. THE normalizer SHALL fill all missing keys with safe defaults (empty strings, empty lists, 0 scores).
3. THE normalizer SHALL clamp `score` to `[0, max_marks]`.
4. THE normalizer SHALL clamp all `criteria_scores[*].score` values to `[0, max_marks * weight]`.
5. THE normalizer SHALL ensure `areas_of_improvement` is a list of dicts with the required keys — defaulting missing keys to empty strings/lists.
6. THE normalizer SHALL ensure `flags.plagiarism_risk` and `flags.ai_generated_risk` are one of `"Low"`, `"Medium"`, `"High"` — defaulting to `"Low"` if missing or invalid.
7. THE normalizer SHALL ensure `benchmarking.percentile` is a float in `[0.0, 100.0]`.
