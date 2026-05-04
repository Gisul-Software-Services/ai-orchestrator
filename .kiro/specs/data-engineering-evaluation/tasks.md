# Implementation Plan: Data Engineering Evaluation

## Overview

Implement the 3-layer data engineering evaluation pipeline (PySpark sandbox + static partial credit + GPT-4o-mini AI review) with synchronous and asynchronous HTTP endpoints, frontend proxy routes, and a comprehensive test suite. Implementation follows the existing SQL/DevOps evaluator patterns throughout.

## Tasks

- [x] 1. Create Pydantic schemas (`eval_schema.py`)
  - Create `backend/model_app/competencies/data_engineering/__init__.py` (empty package marker)
  - Create `backend/model_app/competencies/data_engineering/eval_schema.py` with all models:
    - `TestCase` (input_data, expected_output)
    - `ExecutionResult` (test_case_index, status Literal, output_df, error_message)
    - `DataEngineeringQuestion` (id, title, description, question_type Literal["coding","subjective"], difficulty, rubric_items, test_cases)
    - `DataEngineeringSubmission` (code, answer, execution_results)
    - `DataEngineeringEvalRequest` (question, submission, use_cache)
    - `DataEngineeringEvalResponse` (overall_score, deterministic_score, static_partial_score, ai_score, final_score, score_reason, per_test_case_results, ai_feedback, is_correct)
  - _Requirements: 1.1, 1.2, 1.3, 1.4_

- [x] 2. Update settings
  - Modify `backend/model_app/core/settings.py` to add `openai_api_key: str = ""` and `openai_model: str = "gpt-4o-mini"` fields to `ModelSettings`
  - _Requirements: 6.1_

- [x] 3. Implement the core evaluator (`data_engineering_evaluator.py`)
  - Create `backend/model_app/evaluation/data_engineering_evaluator.py`

  - [x] 3.1 Implement `_normalize_cell` and `_compare_dataframes`
    - `_normalize_cell`: handle None/NaN → None, float with no fractional part → int, str → stripped, bool → bool
    - `_compare_dataframes(actual, expected)`: schema check (cap 40), row count check (cap 60), data check order-agnostic (cap 85), full match (100); return `{is_correct, deterministic_score, score_reason}`
    - `_build_validation_signature(question)`: deterministic string from expected output schema + row count across all test cases
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [x] 3.2 Implement `_run_pyspark_sandbox` and `_run_deterministic_validation`
    - `_run_pyspark_sandbox(code, test_case, timeout=30)`: static import check for `{"os","sys","subprocess","socket","shutil"}` before subprocess launch; run subprocess with timeout; capture stdout as JSON output_df; handle timeout (SIGKILL, status="timeout"), exception (status="failed", traceback[:2000]), success (status="success")
    - `_run_deterministic_validation(question, submission)`: iterate test cases, call sandbox per test case, call `_compare_dataframes`, compute arithmetic mean of per-test-case scores; return `{deterministic_score, per_test_case_results, score_reason}`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.7_

  - [x] 3.3 Implement `_run_static_partial_credit`
    - Define `_PATTERNS` dict (8 patterns, 3 pts each, max 24 pts)
    - Pattern hit points: scan code for each of the 8 regex patterns
    - Rubric token overlap: 0.6 pts per token from question title+description present in code tokens, capped at 12 pts
    - Length bonus: 4 pts if ≥40 unique tokens, 2 pts if ≥20, else 0
    - Return `static_partial_score` clamped to [0, 40]
    - Only called when execution status ∈ {"failed","timeout","cancelled","pending","running"}
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 3.4 Implement `_run_subjective_rubric`
    - Define `_REASONING_TERMS` set (15 terms)
    - Coverage score: (rubric items with ≥50% token overlap / total items) × 55
    - Concept score: (rubric vocab tokens in answer / total rubric vocab tokens) × 15
    - Depth score: min(word_count / 180, 1.0) × 15
    - Structure score: 10 if ≥4 sentences, 7 if ≥2, else 3
    - Reasoning score: 2.5 pts per reasoning term found, capped at 10
    - Apply word-count penalties (< 20 words → cap 10; < 40 → multiply 0.45; < 70 → multiply 0.70)
    - Apply copy-paste detection (similarity ≥88% AND novel tokens <25% → cap 8; similarity ≥75% AND novel tokens <35% → cap 22)
    - Apply coverage penalty (coverage ratio < 25% → cap 35)
    - Return `rubric_score` in [0, 100]
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.9, 5.10, 5.11, 5.12_

  - [x] 3.5 Implement `_run_ai_review`
    - Build Redis cache key via SHA-256 of `code_or_answer + question_id + validation_signature`
    - Check Redis (synchronous client at `settings.redis_url`); on hit log INFO and return cached response
    - Build OpenAI prompt: system prompt `"You are an expert Data Engineer. Generate concise, high-quality PySpark questions. Return ONLY valid JSON."` + user prompt with question/submission context
    - Call `openai.OpenAI(api_key=settings.openai_api_key).chat.completions.create(model=settings.openai_model, temperature=0.1, max_tokens=6000, response_format={"type":"json_object"}, messages=[...])`
    - Retry up to 3 times with exponential backoff (1s, 2s, 4s); max total wait 60s
    - On all retries exhausted: return `{ai_score: None, ai_feedback: {}}`, log WARNING
    - On success: parse JSON response, store in Redis with TTL=86400s, return AI feedback dict
    - Handle Redis unavailable: log WARNING, proceed without caching, do not raise
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 11.1, 11.2, 11.3, 11.4, 11.5_

  - [x] 3.6 Implement `_resolve_final_score`
    - Default: `final_score = deterministic_score`
    - AI fallback: if `score_reason ∈ FALLBACK_REASONS` AND `det_score == 0` AND `ai_score is not None` → `final_score = ai_score`
    - Static override: if `static_score > ai_score` (and `ai_score is not None`) → `final_score = static_score`
    - Clamp `final_score` to [0, 100]
    - Always return non-empty `score_reason`
    - Define `FALLBACK_REASONS = {"missing_execution_result","missing_validation_result","failed","timeout","cancelled","pending","running"}`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

  - [x] 3.7 Implement `get_data_engineering_feedback` orchestrator
    - Accept `payload: dict, usage_meta: dict | None`
    - Validate question_type; dispatch to coding or subjective path
    - Coding path: call `_run_deterministic_validation`; if any test case failed/timeout call `_run_static_partial_credit`
    - Subjective path: call `_run_subjective_rubric` (result stored as `static_partial_score`; `deterministic_score = 0`)
    - Both paths: call `_run_ai_review`
    - Call `_resolve_final_score` to produce `final_score`
    - Call `emit_eval_usage` with route `"data_engineering_evaluation"`, latency_ms, cache_hit status
    - On AI failure: call `emit_eval_usage` with `status="error"` and error detail
    - Return `DataEngineeringEvalResponse`-compatible dict
    - _Requirements: 12.1, 12.2, 12.3_

- [ ] 4. Checkpoint — verify evaluator logic
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Add backend routes to `evaluation.py`
  - Modify `backend/model_app/api/routes/evaluation.py`:
    - Add import for `DataEngineeringEvalRequest` from `backend.model_app.competencies.data_engineering.eval_schema`
    - Add import for `get_data_engineering_feedback` from `backend.model_app.evaluation.data_engineering_evaluator`
    - Add `POST /data-engineering` synchronous route: accept `DataEngineeringEvalRequest`, call `get_data_engineering_feedback`, return HTTP 200 with result; bind usage meta; return HTTP 422 on validation failure (automatic via Pydantic)
    - Add `POST /data-engineering/async` route: enqueue background job, set initial status "pending", create `asyncio.create_task(_run())`, update to "processing" when task starts, update to "complete"/"failed" on finish/error; acquire `llm_semaphore`; return `{job_id, status: "pending"}` immediately
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.6_

- [x] 6. Add frontend proxy routes and endpoint registry entry
  - [x] 6.1 Create `frontend/web/app/api/admin/evaluate/data-engineering/route.ts`
    - Single line: `export const POST = makeAdminProxyPost("/api/v1/evaluation/data-engineering");`
    - _Requirements: 10.1, 10.4_

  - [x] 6.2 Create `frontend/web/app/api/admin/evaluate/data-engineering-async/route.ts`
    - Single line: `export const POST = makeAdminProxyPost("/api/v1/evaluation/data-engineering/async");`
    - _Requirements: 10.2, 10.4_

  - [x] 6.3 Modify `frontend/web/lib/endpoints.ts`
    - Add entry to `API_ENDPOINTS` array: `{ id: "evaluate-data-engineering", path: "/api/v1/evaluation/data-engineering/async", method: "POST", label: "Data Engineering Evaluation", section: "evaluation", implemented: true }`
    - _Requirements: 10.3_

- [ ] 7. Write property-based tests (Hypothesis)

  - [ ]* 7.1 Write property test for schema round-trip (Property 1)
    - **Property 1: Schema validation round-trip**
    - Generate valid `DataEngineeringEvalRequest` dicts, serialise via `model_dump()`, re-parse with `model_validate()`, assert equivalence
    - File: `backend/tests/evaluation/test_data_engineering_schema.py`
    - **Validates: Requirements 1.1, 1.2**

  - [ ]* 7.2 Write property test for invalid question_type rejection (Property 2)
    - **Property 2: Invalid question_type is always rejected**
    - Generate arbitrary strings not in `{"coding","subjective"}`, assert `ValidationError` is raised
    - File: `backend/tests/evaluation/test_data_engineering_schema.py`
    - **Validates: Requirements 1.4**

  - [ ]* 7.3 Write property test for cell normalisation equivalences (Property 3)
    - **Property 3: Cell normalisation produces stable equivalences**
    - Generate semantically-equal value pairs per normalisation rule, assert `_normalize_cell(a) == _normalize_cell(b)`
    - File: `backend/tests/evaluation/test_data_engineering_comparator.py`
    - **Validates: Requirements 3.2**

  - [ ]* 7.4 Write property test for DataFrame comparison score caps (Property 4)
    - **Property 4: DataFrame comparison score caps are respected**
    - Generate DataFrame pairs with controlled mismatch types, assert score caps (≤40, ≤60, ≤85, ==100)
    - File: `backend/tests/evaluation/test_data_engineering_comparator.py`
    - **Validates: Requirements 3.3, 3.4, 3.5, 3.6**

  - [ ]* 7.5 Write property test for multi-test-case arithmetic mean (Property 5)
    - **Property 5: Multi-test-case deterministic score is the arithmetic mean**
    - Generate lists of per-test-case scores (N ≥ 1), assert overall score equals arithmetic mean
    - File: `backend/tests/evaluation/test_data_engineering_comparator.py`
    - **Validates: Requirements 3.7**

  - [ ]* 7.6 Write property test for static score bounded in [0, 40] (Property 6)
    - **Property 6: Static partial credit is bounded in [0, 40]**
    - Generate arbitrary code strings and questions, assert `0 <= result <= 40`
    - File: `backend/tests/evaluation/test_data_engineering_static.py`
    - **Validates: Requirements 4.5**

  - [ ]* 7.7 Write property test for pattern score proportionality (Property 7)
    - **Property 7: Static pattern score is proportional to matched patterns**
    - Generate code with exactly K of 8 patterns (K ∈ {0..8}), assert pattern contribution == `min(3*K, 24)`
    - File: `backend/tests/evaluation/test_data_engineering_static.py`
    - **Validates: Requirements 4.2**

  - [ ]* 7.8 Write property test for rubric component bounds (Property 8)
    - **Property 8: Rubric component scores are within their declared maxima**
    - Generate arbitrary answers and rubric items, assert each component within declared max
    - File: `backend/tests/evaluation/test_data_engineering_rubric.py`
    - **Validates: Requirements 5.1, 5.2, 5.3, 5.4, 5.5, 5.6**

  - [ ]* 7.9 Write property test for rubric penalty rules (Property 9)
    - **Property 9: Rubric penalty rules are applied correctly**
    - Generate answers with controlled word counts and similarity ratios, assert each penalty cap is respected
    - File: `backend/tests/evaluation/test_data_engineering_rubric.py`
    - **Validates: Requirements 5.7, 5.8, 5.9, 5.10, 5.11, 5.12**

  - [ ]* 7.10 Write property test for security import blocking (Property 10)
    - **Property 10: Security import blocking covers all blocked modules**
    - Generate code strings containing imports of each blocked module (all import forms), assert `status="failed"` with security violation message
    - File: `backend/tests/evaluation/test_data_engineering_sandbox.py`
    - **Validates: Requirements 2.5**

  - [ ]* 7.11 Write property test for final score clamping (Property 11)
    - **Property 11: Final score is always clamped to [0, 100]**
    - Generate arbitrary float triples for det_score, static_score, ai_score, assert `0.0 <= final_score <= 100.0`
    - File: `backend/tests/evaluation/test_data_engineering_resolver.py`
    - **Validates: Requirements 7.4**

  - [ ]* 7.12 Write property test for score resolution rules (Property 12)
    - **Property 12: Score resolution follows the deterministic override rules**
    - Generate inputs matching each resolution condition (default, AI fallback, static override), assert correct `final_score` and non-empty `score_reason`
    - File: `backend/tests/evaluation/test_data_engineering_resolver.py`
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.5**

- [ ] 8. Write unit tests

  - [ ]* 8.1 Write unit tests for Pydantic schemas
    - Valid request round-trip; missing required fields → HTTP 422; invalid question_type → ValidationError; valid coding and subjective requests accepted
    - File: `backend/tests/evaluation/test_data_engineering_schema.py`
    - _Requirements: 1.1, 1.2, 1.3, 1.4_

  - [ ]* 8.2 Write unit tests for DataFrame comparator
    - `_normalize_cell` with concrete values: None, float('nan'), 3.0, " foo ", True
    - `_compare_dataframes` with identical DataFrames (score=100, is_correct=True), schema mismatch (score≤40), row count mismatch (score≤60), data mismatch (score≤85)
    - File: `backend/tests/evaluation/test_data_engineering_comparator.py`
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6_

  - [ ]* 8.3 Write unit tests for static partial credit scorer
    - Code with 0 patterns → score=0 (plus any length/overlap bonus); code with 4 patterns → pattern contribution=12; code with all 8 patterns → pattern contribution=24; total capped at 40
    - File: `backend/tests/evaluation/test_data_engineering_static.py`
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 8.4 Write unit tests for subjective rubric scorer
    - Short answer (<20 words) → score≤10; copy-paste answer → score≤8; well-structured answer with reasoning terms → score reflects all components; coverage ratio <25% → score≤35
    - File: `backend/tests/evaluation/test_data_engineering_rubric.py`
    - _Requirements: 5.1–5.12_

  - [ ]* 8.5 Write unit tests for PySpark sandbox
    - Security import detection for all 5 blocked modules (import X, from X import Y forms) → status="failed"; timeout → status="timeout"; successful execution → status="success" with output_df; exception in code → status="failed" with traceback
    - File: `backend/tests/evaluation/test_data_engineering_sandbox.py`
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 8.6 Write unit tests for score resolver
    - Default path: final_score == det_score; AI fallback path: reason ∈ FALLBACK_REASONS, det_score=0, ai_score set → final_score=ai_score; static override: static_score > ai_score → final_score=static_score; clamping: out-of-range inputs → [0,100]
    - File: `backend/tests/evaluation/test_data_engineering_resolver.py`
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_

- [ ] 9. Final checkpoint — ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests (P1–P12) validate universal correctness properties using Hypothesis; run with `pytest backend/tests/evaluation/ --hypothesis-seed=0`
- Unit tests validate specific examples and edge cases
- The evaluator uses GPT-4o-mini (OpenAI) rather than the local Qwen/vLLM model — `openai_api_key` must be set in `.env` for AI review to function; the evaluator degrades gracefully (ai_score=None) if the key is absent or the API is unreachable
- Redis caching uses a synchronous `redis.Redis` client (not the async one in `services/cache.py`); the cache key is SHA-256 of `code_or_answer + question_id + validation_signature` with TTL=86400s
