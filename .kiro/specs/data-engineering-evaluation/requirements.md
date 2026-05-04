# Requirements Document

## Introduction

This feature adds a Data Engineering competency evaluation endpoint to the assessment platform. Candidates submit PySpark code (coding questions) or written answers (subjective questions). The system scores submissions through a 3-layer pipeline: deterministic validation (PySpark sandbox execution + DataFrame comparison), static partial credit (pattern matching fallback), and AI review (GPT-4o-mini). The final score is resolved by a deterministic override rule. Both synchronous and asynchronous HTTP endpoints are exposed, mirroring the existing SQL and DevOps evaluation patterns.

## Glossary

- **Evaluator**: The backend Python module (`data_engineering_evaluator.py`) that orchestrates the 3-layer scoring pipeline.
- **Sandbox**: The isolated PySpark execution environment that runs candidate-submitted code against test cases.
- **Deterministic_Validator**: The component that executes candidate code in the Sandbox and compares the resulting DataFrame against the expected output.
- **Static_Scorer**: The component that applies pattern-matching partial credit when execution did not complete.
- **AI_Reviewer**: The GPT-4o-mini-based component that produces qualitative feedback and an AI score.
- **Score_Resolver**: The logic that combines deterministic, static, and AI scores into a single final score.
- **DataFrame_Comparator**: The sub-component of the Deterministic_Validator that compares schema, row count, and cell values between actual and expected DataFrames.
- **Rubric_Scorer**: The component that applies deterministic text analysis to subjective answers before AI review.
- **Redis_Cache**: The Redis instance (keyed by SHA-256 of code + question + validation signature, TTL 24 hours) used to cache AI_Reviewer responses.
- **Evaluation_Router**: The FastAPI router that exposes `/api/v1/evaluation/data-engineering` (sync) and `/api/v1/evaluation/data-engineering/async` (async) endpoints.
- **Proxy_Route**: The Next.js API route that forwards admin requests to the Evaluation_Router through the backend gateway.
- **Job_Store**: The existing async job store used by all async evaluation endpoints to track background job status.
- **Test_Case**: A single input/expected-output pair used to evaluate a coding question; a question may have multiple test cases.
- **Validation_Signature**: A deterministic string derived from the expected output schema and row count, used as part of the Redis cache key.

---

## Requirements

### Requirement 1: Pydantic Request and Response Schemas

**User Story:** As a backend developer, I want well-typed Pydantic models for the data engineering evaluation request and response, so that the API contract is explicit and validated at the boundary.

#### Acceptance Criteria

1. THE Evaluation_Router SHALL accept requests conforming to a `DataEngineeringEvalRequest` Pydantic model that includes: `question` (id, title, description, question_type `"coding"` or `"subjective"`, difficulty, rubric items, test cases), `submission` (code or answer text, execution result per test case), and `use_cache` flag.
2. THE Evaluation_Router SHALL return responses conforming to a `DataEngineeringEvalResponse` Pydantic model that includes: `overall_score` (float 0–100), `deterministic_score` (float), `static_partial_score` (float), `ai_score` (float or null), `final_score` (float), `score_reason` (string), `per_test_case_results` (list), `ai_feedback` (object), and `is_correct` (bool).
3. IF a request body is missing required fields, THEN THE Evaluation_Router SHALL return HTTP 422 with a validation error detail.
4. THE `DataEngineeringEvalRequest` SHALL accept `question_type` values of exactly `"coding"` or `"subjective"` and reject all other values with HTTP 422.

---

### Requirement 2: PySpark Sandbox Execution

**User Story:** As the platform, I want to execute candidate PySpark code in an isolated sandbox, so that the output DataFrame can be compared against the expected result without affecting the host environment.

#### Acceptance Criteria

1. WHEN a coding submission is received, THE Sandbox SHALL execute the candidate's PySpark code in an isolated subprocess with a configurable timeout (default 30 seconds).
2. IF execution exceeds the timeout, THEN THE Sandbox SHALL terminate the subprocess and return an execution result with `status = "timeout"` and `output_df = null`.
3. IF the candidate code raises an unhandled exception, THEN THE Sandbox SHALL capture the traceback and return an execution result with `status = "failed"` and `error_message` containing the traceback (truncated to 2000 characters).
4. WHEN execution completes successfully, THE Sandbox SHALL return an execution result with `status = "success"` and the output DataFrame serialised as a list of row dicts.
5. THE Sandbox SHALL prevent candidate code from importing `os`, `sys`, `subprocess`, `socket`, or `shutil` modules, returning `status = "failed"` with a security violation message if any such import is detected.
6. WHILE a coding question has multiple test cases, THE Sandbox SHALL execute each test case independently and return a separate execution result per test case.

---

### Requirement 3: DataFrame Comparison (Deterministic Validation)

**User Story:** As the platform, I want to compare the candidate's output DataFrame against the expected output using schema, row count, and cell value checks, so that correctness can be determined objectively.

#### Acceptance Criteria

1. WHEN execution succeeds, THE DataFrame_Comparator SHALL compare the actual output DataFrame against the expected output DataFrame for schema match (column names and data types), row count match, and data match (cell values, order-agnostic by default).
2. THE DataFrame_Comparator SHALL normalise cell values before comparison: `None` and `NaN` SHALL be treated as equal; floats with no fractional part (e.g. `3.0`) SHALL be treated as equal to their integer equivalent (`3`); strings SHALL be stripped of leading and trailing whitespace; booleans SHALL be normalised to Python `bool`.
3. WHEN all three checks pass, THE DataFrame_Comparator SHALL set `is_correct = True` and `deterministic_score = 100`.
4. WHEN schema does not match, THE DataFrame_Comparator SHALL set `is_correct = False` and cap `deterministic_score` at 40.
5. WHEN schema matches but row count does not match, THE DataFrame_Comparator SHALL set `is_correct = False` and cap `deterministic_score` at 60.
6. WHEN schema and row count match but data does not match, THE DataFrame_Comparator SHALL set `is_correct = False` and cap `deterministic_score` at 85.
7. WHEN a coding question has multiple test cases, THE Evaluator SHALL compute the `deterministic_score` as the arithmetic mean of the per-test-case deterministic scores.

---

### Requirement 4: Static Partial Credit Scoring (Fallback)

**User Story:** As the platform, I want to award partial credit based on code patterns when execution fails, so that candidates who write structurally correct but non-executable code receive some score.

#### Acceptance Criteria

1. THE Static_Scorer SHALL apply static partial credit scoring only when the execution `status` is one of: `"failed"`, `"timeout"`, `"cancelled"`, `"pending"`, or `"running"`.
2. THE Static_Scorer SHALL award pattern hit points (maximum 24 points total, 3 points each) for the presence of each of the following patterns in the submitted code: SparkSession creation, data reading (`.read`, `.csv`, `.parquet`, `.json`), schema or cast operations, null handling (`fillna`, `dropna`, `isNull`), column transformations (`withColumn`, `when`/`otherwise`), aggregations (`groupBy`, `agg`, `count`, `sum`), Spark SQL usage, and write operations.
3. THE Static_Scorer SHALL award rubric token overlap points (maximum 12 points) calculated as 0.6 points per token from the question title and description that also appears in the submitted code tokens, capped at 12.
4. THE Static_Scorer SHALL award a code length bonus: 4 points if the submission contains 40 or more unique tokens, 2 points if it contains 20 or more unique tokens, and 0 points otherwise.
5. THE Static_Scorer SHALL produce a `static_partial_score` in the range [0, 40].

---

### Requirement 5: Subjective Rubric Scoring

**User Story:** As the platform, I want to deterministically score written answers against a rubric before AI review, so that scoring is consistent and reproducible for subjective questions.

#### Acceptance Criteria

1. WHEN a subjective submission is received, THE Rubric_Scorer SHALL compute a rubric score (maximum 100 points) composed of: coverage score (55 pts max), concept score (15 pts max), depth score (15 pts max), structure score (10 pts max), and reasoning score (10 pts max).
2. THE Rubric_Scorer SHALL compute the coverage score as: `(count of rubric items where token overlap with answer ≥ 50%) / (total rubric items) × 55`.
3. THE Rubric_Scorer SHALL compute the concept score as: `(count of rubric vocabulary tokens present in answer) / (total rubric vocabulary tokens) × 15`.
4. THE Rubric_Scorer SHALL compute the depth score as: `min(word_count / 180, 1.0) × 15`.
5. THE Rubric_Scorer SHALL compute the structure score as: 10 if the answer contains 4 or more sentences, 7 if it contains 2 or more sentences, and 3 otherwise.
6. THE Rubric_Scorer SHALL compute the reasoning score as: 2.5 points per reasoning term found in the answer from the set: `because`, `tradeoff`, `latency`, `throughput`, `schema`, `quality`, `monitoring`, `partitioning`, `checkpoint`, `deduplicate`, `watermark`, `backfill`, `rollback`, `governance`, `lineage`, capped at 10 points.
7. IF the answer contains fewer than 20 words, THEN THE Rubric_Scorer SHALL cap the rubric score at 10.
8. IF the answer contains fewer than 40 words, THEN THE Rubric_Scorer SHALL multiply the rubric score by 0.45.
9. IF the answer contains fewer than 70 words, THEN THE Rubric_Scorer SHALL multiply the rubric score by 0.70.
10. IF the answer token similarity to the question text is 88% or greater AND the answer contains fewer than 25% novel tokens, THEN THE Rubric_Scorer SHALL cap the rubric score at 8 (copy-paste detection).
11. IF the answer token similarity to the question text is 75% or greater AND the answer contains fewer than 35% novel tokens, THEN THE Rubric_Scorer SHALL cap the rubric score at 22.
12. IF the coverage ratio is less than 25%, THEN THE Rubric_Scorer SHALL cap the rubric score at 35.

---

### Requirement 6: AI Review via GPT-4o-mini

**User Story:** As the platform, I want to obtain qualitative AI feedback and an AI score from GPT-4o-mini for every submission, so that candidates receive actionable improvement suggestions beyond deterministic scoring.

#### Acceptance Criteria

1. THE AI_Reviewer SHALL call the OpenAI API using the model specified in `settings.OPENAI_MODEL` (default `gpt-4o-mini`) with `temperature = 0.1`, `max_tokens = 6000`, and `response_format = {"type": "json_object"}`.
2. THE AI_Reviewer SHALL use the system prompt: `"You are an expert Data Engineer. Generate concise, high-quality PySpark questions. Return ONLY valid JSON."`.
3. WHEN reviewing a coding submission, THE AI_Reviewer SHALL include in the user prompt: the question title, description, candidate code, execution status, and per-test-case results; and SHALL request feedback covering correctness, performance, best practices, improvement suggestions, and alternative approaches.
4. WHEN reviewing a subjective submission, THE AI_Reviewer SHALL include in the user prompt: the question title, description, rubric items, and candidate answer; and SHALL request feedback covering technical accuracy, depth of understanding, completeness, practical application, communication, and industry knowledge.
5. THE AI_Reviewer SHALL return a response conforming to the shape: `{ "overall_score": float, "correctness_feedback": str, "performance_feedback": str, "best_practices_feedback": str, "improvement_suggestions": [str], "strengths": [str], "areas_for_improvement": [str], "code_examples": [...], "alternative_approaches": [...] }`.
6. IF the OpenAI API call fails, THEN THE AI_Reviewer SHALL retry up to 3 times with exponential backoff, with a maximum total wait of 60 seconds before returning `ai_score = null` and empty feedback.
7. THE Redis_Cache SHALL store AI_Reviewer responses keyed by the SHA-256 hash of the concatenation of: candidate code (or answer), question id, and Validation_Signature; with a TTL of 24 hours (86400 seconds).
8. WHEN a cache entry exists for the request key, THE AI_Reviewer SHALL return the cached response without calling the OpenAI API.

---

### Requirement 7: Final Score Resolution

**User Story:** As the platform, I want a deterministic rule to combine the three scoring layers into a single final score, so that the result is predictable and the deterministic layer always takes precedence when it has meaningful data.

#### Acceptance Criteria

1. THE Score_Resolver SHALL set `final_score = deterministic_score` as the default resolution.
2. IF `score_reason` is one of `"missing_execution_result"`, `"missing_validation_result"`, `"failed"`, `"timeout"`, `"cancelled"`, `"pending"`, or `"running"` AND `deterministic_score == 0` AND `ai_score` is not null, THEN THE Score_Resolver SHALL set `final_score = ai_score`.
3. IF `static_partial_score > ai_score` (where `ai_score` is not null), THEN THE Score_Resolver SHALL set `final_score = static_partial_score`.
4. THE Score_Resolver SHALL clamp `final_score` to the range [0, 100].
5. THE Score_Resolver SHALL include `score_reason` in the response to indicate which scoring path determined the final score.

---

### Requirement 8: Synchronous Evaluation Endpoint

**User Story:** As an API consumer, I want a synchronous POST endpoint for data engineering evaluation, so that I can receive the full evaluation result in a single HTTP response for low-latency use cases.

#### Acceptance Criteria

1. THE Evaluation_Router SHALL expose `POST /api/v1/evaluation/data-engineering` that accepts a `DataEngineeringEvalRequest` body and returns a `DataEngineeringEvalResponse` synchronously.
2. WHEN the evaluation completes successfully, THE Evaluation_Router SHALL return HTTP 200 with the full evaluation result.
3. IF the request payload is empty or missing required fields, THEN THE Evaluation_Router SHALL return HTTP 422.
4. THE Evaluation_Router SHALL bind usage metadata from the HTTP request for billing using the existing `bind_usage_meta_from_request` pattern.

---

### Requirement 9: Asynchronous Evaluation Endpoint

**User Story:** As an API consumer, I want an asynchronous POST endpoint for data engineering evaluation, so that I can avoid timeouts when submitting multiple evaluations concurrently.

#### Acceptance Criteria

1. THE Evaluation_Router SHALL expose `POST /api/v1/evaluation/data-engineering/async` that accepts a `DataEngineeringEvalRequest` body, enqueues the evaluation as a background job, and returns `{ "job_id": str, "status": "pending" }` immediately (HTTP 200).
2. THE Evaluation_Router SHALL store the job in the Job_Store with initial status `"pending"` before returning the response.
3. WHEN the background job starts, THE Evaluation_Router SHALL update the job status to `"processing"` in the Job_Store.
4. WHEN the background job completes successfully, THE Evaluation_Router SHALL update the job status to `"complete"` and store the full `DataEngineeringEvalResponse` as the job result in the Job_Store.
5. IF the background job raises an exception, THEN THE Evaluation_Router SHALL update the job status to `"failed"` and store the error message in the Job_Store.
6. THE Evaluation_Router SHALL acquire the existing `llm_semaphore` before executing the evaluation in the background thread, consistent with all other async evaluation endpoints.

---

### Requirement 10: Frontend Proxy Routes

**User Story:** As a frontend developer, I want Next.js API proxy routes for the data engineering evaluation endpoints, so that the admin UI can call them through the standard authenticated proxy pattern.

#### Acceptance Criteria

1. THE Proxy_Route at `frontend/web/app/api/admin/evaluate/data-engineering/route.ts` SHALL proxy `POST` requests to `/api/v1/evaluation/data-engineering` using `makeAdminProxyPost`.
2. THE Proxy_Route at `frontend/web/app/api/admin/evaluate/data-engineering-async/route.ts` SHALL proxy `POST` requests to `/api/v1/evaluation/data-engineering/async` using `makeAdminProxyPost`.
3. THE `API_ENDPOINTS` registry in `frontend/web/lib/endpoints.ts` SHALL contain an entry with `id = "evaluate-data-engineering"`, `path = "/api/v1/evaluation/data-engineering/async"`, `method = "POST"`, `label = "Data Engineering Evaluation"`, `section = "evaluation"`, and `implemented = true`.
4. WHEN an unauthenticated request reaches a Proxy_Route, THE Proxy_Route SHALL return HTTP 401, consistent with all other admin proxy routes.

---

### Requirement 11: Redis Caching for AI Review

**User Story:** As the platform operator, I want AI review responses cached in Redis for 24 hours, so that repeated evaluations of identical submissions do not incur unnecessary OpenAI API costs.

#### Acceptance Criteria

1. THE Redis_Cache SHALL use the Redis instance at the URL configured in `settings.redis_url`.
2. THE Redis_Cache SHALL store serialised AI_Reviewer responses as JSON strings with a TTL of 86400 seconds.
3. THE Redis_Cache key SHALL be the hex-encoded SHA-256 digest of the concatenation of: candidate submission text, question id, and Validation_Signature.
4. WHEN a cache entry is found, THE AI_Reviewer SHALL log a cache hit at INFO level and return the cached response without calling the OpenAI API.
5. IF the Redis connection is unavailable, THEN THE AI_Reviewer SHALL proceed without caching and log a WARNING, without raising an exception to the caller.

---

### Requirement 12: Billing and Usage Tracking

**User Story:** As the platform operator, I want evaluation usage to be tracked for billing, so that OpenAI API costs and model inference costs are attributed correctly.

#### Acceptance Criteria

1. THE Evaluator SHALL call `emit_eval_usage` (from `backend.model_app.evaluation.base`) after every evaluation, passing the route name `"data_engineering_evaluation"`, latency in milliseconds, and cache hit status.
2. WHEN the AI_Reviewer returns a cached response, THE Evaluator SHALL call `emit_eval_usage` with `cache_hit = True` and `latency_ms = 0`.
3. IF the AI_Reviewer call fails after all retries, THE Evaluator SHALL call `emit_eval_usage` with `status = "error"` and the error detail string.
