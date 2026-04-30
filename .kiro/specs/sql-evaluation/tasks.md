# Implementation Plan: SQL AI Evaluation

## Overview

Add `POST /api/v1/evaluation/sql` to the model service following the exact DSA/AIML evaluator pattern. Three files are touched: a new Pydantic schema module, a new evaluator module, and a one-route addition to the existing evaluation router.

## Tasks

- [x] 1. Create Pydantic models in `backend/model_app/competencies/sql/eval_schema.py`
  - Define `TestResult` nested model (`passed`, `user_output`, `expected_output`, `error`)
  - Define `SQLEvaluationRequest` with all required and optional fields from Requirement 1.2
  - Define `CriterionScore` nested model (`score`, `weight`, `feedback`)
  - Define `SQLAIFeedback` with all top-level keys matching the contract in Requirement 5.1 (`question_type: Literal["SQL"]`, `evaluation_version: str = "2.1.0"`, `ai_generated: bool = True`)
  - _Requirements: 1.2, 5.1, 5.2, 5.6_

- [x] 2. Implement `backend/model_app/evaluation/sql_evaluator.py` — core helpers
  - [x] 2.1 Implement module-level cache and system prompt constant
    - `_cache = TTLCache(maxsize=500, ttl=3600)` matching Requirement 2.1
    - `_SYSTEM_PROMPT` string with all five criteria weights, Big-O ban, floor/cap hint, and minified-JSON instruction matching Requirements 3.1–3.5
    - _Requirements: 2.1, 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 2.2 Implement `_build_user_prompt(req: dict) -> str`
    - Include all fields listed in Requirement 3.6 with truncation limits from the design (desc→1000, schemas→800, user_output/expected_output→500, error→300)
    - _Requirements: 3.6, 3.7_

  - [x] 2.3 Implement `_empty_response_dict() -> dict` and `_empty_response(req: dict) -> dict`
    - `_empty_response_dict` returns a fully-keyed dict with safe defaults matching the full contract (score=0, all lists empty, all strings "")
    - `_empty_response` sets `flags.incomplete_answer=True`, `score=0`, `submitted_answer=req["user_query"]`, `expected_answer=""`
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 7.1, 7.2_

  - [ ]* 2.4 Write property test for `_empty_response` — Property 11
    - **Property 11: Whitespace queries set incomplete_answer flag**
    - **Validates: Requirements 5.4, 7.1, 7.2**
    - Use `hypothesis.strategies.text(alphabet=string.whitespace)` including empty string
    - Assert `result["flags"]["incomplete_answer"] is True` and `result["score"] == 0`

  - [x] 2.5 Implement `_normalize_product(raw: dict, max_marks: float) -> dict`
    - Start from `_empty_response_dict()`, copy only known keys from `raw`
    - Clamp `score` to `[0, max_marks]`; clamp each `criteria_scores[k]["score"]` to `[0, max_marks * weight[k]]`
    - Ensure `feedback` dict has all five keys; ensure `answer_log` has all required keys and forces `expected_answer=""`
    - Ensure `areas_of_improvement` is a list of dicts with required keys defaulting to `""` / `[]`
    - Clamp `benchmarking.percentile` to `[0.0, 100.0]`
    - Validate `flags.plagiarism_risk` and `flags.ai_generated_risk` to `{"Low","Medium","High"}`, default `"Low"`
    - Force `ai_generated=True`, `question_type="SQL"`, `evaluation_version="2.1.0"`
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7, 5.2, 5.6_

  - [ ]* 2.6 Write property test for `_normalize_product` — Property 14
    - **Property 14: Normalizer fills all missing keys**
    - **Validates: Requirements 9.1, 9.2**
    - Use `hypothesis.strategies.fixed_dictionaries({})` and `hypothesis.strategies.dictionaries(...)` including empty dict `{}`
    - Assert every key required by `SQLAIFeedback` contract is present in the result

  - [ ]* 2.7 Write property test for `_normalize_product` — Property 15
    - **Property 15: Normalizer clamps scores to valid ranges**
    - **Validates: Requirements 9.3, 9.4, 9.7**
    - Generate random dicts with arbitrary numeric values for `score`, `criteria_scores[*].score`, `benchmarking.percentile`
    - Assert `result["score"]` in `[0, max_marks]`, each criterion score in `[0, max_marks * weight]`, percentile in `[0.0, 100.0]`

  - [ ]* 2.8 Write property test for `_normalize_product` — Property 16
    - **Property 16: Risk flags are valid enum values**
    - **Validates: Requirements 9.6**
    - Generate random dicts with arbitrary strings for `flags.plagiarism_risk` and `flags.ai_generated_risk`
    - Assert both are in `{"Low", "Medium", "High"}` after normalization

  - [x] 2.9 Implement `_enforce_score(result: dict, passed: bool, max_marks: float) -> dict`
    - Apply floor (`max(score, max_marks * 0.8)`) when `passed=True`, cap (`min(score, max_marks * 0.5)`) when `passed=False`
    - Clamp final score to `[0, max_marks]`
    - Recompute `percentage = round((score / max_marks) * 100, 2)`
    - Redistribute `criteria_scores` proportionally so weighted sum equals clamped score (handle zero weighted_sum edge case)
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 2.10 Write property test for `_enforce_score` — Property 5
    - **Property 5: Score floor/cap enforcement**
    - **Validates: Requirements 4.1, 4.2, 4.3**
    - Generate `(raw_score, max_marks > 0, passed)` via `hypothesis.strategies`
    - Assert: if `passed=True` → `result["score"] >= max_marks * 0.8`; if `passed=False` → `result["score"] <= max_marks * 0.5`; always `0 <= result["score"] <= max_marks`

  - [ ]* 2.11 Write property test for `_enforce_score` — Property 6
    - **Property 6: Percentage is always consistent with score**
    - **Validates: Requirements 4.4**
    - Assert `result["percentage"] == round((result["score"] / max_marks) * 100, 2)` for all `max_marks > 0`

  - [ ]* 2.12 Write property test for `_enforce_score` — Property 7
    - **Property 7: Criteria weighted sum equals overall score**
    - **Validates: Requirements 4.5**
    - Assert `abs(sum(criteria[k]["score"] * weights[k] for k in weights) - result["score"]) < 1e-4`

  - [x] 2.13 Implement `_fallback_response(req: dict) -> dict`
    - Score: `max_marks * 0.8` if `passed=True`, `max_marks * 0.3` if `passed=False`
    - Set `flags.requires_human_review=True`, `feedback.summary="Automated scoring applied. Human review recommended."`
    - Distribute criteria scores proportionally by weight
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5_

  - [ ]* 2.14 Write property test for `_fallback_response` — Property 13
    - **Property 13: Fallback scores are deterministic**
    - **Validates: Requirements 6.2, 6.3**
    - Generate `max_marks > 0` via `hypothesis.strategies.floats(min_value=0.01, max_value=1000)`
    - Assert `score == max_marks * 0.8` when `passed=True`, `score == max_marks * 0.3` when `passed=False`

- [x] 3. Implement `get_sql_feedback` public entry point in `sql_evaluator.py`
  - [x] 3.1 Implement cache lookup and empty-query short-circuit
    - Build cache key: `hashlib.md5(f"{question_id}:{user_query}:{passed}".encode()).hexdigest()`
    - Return `_empty_response(req)` immediately if `user_query` is empty or `len(user_query.strip()) < 10`
    - On cache hit with `use_cache=True`: call `emit_eval_usage(..., cache_hit=True, latency_ms=0)` and return cached result
    - _Requirements: 2.2, 2.3, 2.4, 7.1, 7.2, 7.3, 8.1, 8.3_

  - [ ]* 3.2 Write property test for cache key — Property 3
    - **Property 3: Cache key is deterministic**
    - **Validates: Requirements 2.2**
    - Generate random `(question_id, user_query, passed)` triples
    - Assert computed key equals `md5(f"{question_id}:{user_query}:{passed}".encode()).hexdigest()`

  - [x] 3.3 Implement Qwen call, normalization, score enforcement, and cache store
    - Call `_llm_chat_coder(messages, temperature=0.0, max_tokens=700)`, measure `latency_ms`
    - Call `safe_parse(raw)` → if `parse_error=True` treat as exception and apply fallback
    - Call `_normalize_product(parsed, max_marks)` then `_enforce_score(result, passed, max_marks)`
    - Set `answer_log.submitted_answer = req["user_query"]` and `answer_log.expected_answer = ""`
    - Store result in `_cache[cache_key]`; call `emit_eval_usage(..., cache_hit=False, latency_ms=latency_ms)`
    - On exception: `logger.warning(...)`, apply `_fallback_response(req)`, call `emit_eval_usage(..., status="error", error_detail=str(e))`
    - _Requirements: 2.5, 3.1, 4.1–4.5, 5.2, 5.3, 5.5, 6.1, 6.6, 6.7, 8.1, 8.4, 8.5_

  - [ ]* 3.4 Write property test for `answer_log` fields — Property 9
    - **Property 9: expected_answer is always empty string**
    - **Validates: Requirements 5.2**
    - Mock `_llm_chat_coder` to return a valid JSON string; generate valid request dicts
    - Assert `result["answer_log"]["expected_answer"] == ""`

  - [ ]* 3.5 Write property test for `answer_log.submitted_answer` — Property 10
    - **Property 10: submitted_answer equals user_query**
    - **Validates: Requirements 5.3**
    - Generate valid request dicts with random `user_query` strings (len >= 10 non-whitespace)
    - Assert `result["answer_log"]["submitted_answer"] == req["user_query"]`

  - [ ]* 3.6 Write property test for fallback on Qwen exception — Property 12
    - **Property 12: Fallback sets requires_human_review**
    - **Validates: Requirements 5.5, 6.1**
    - Mock `_llm_chat_coder` to raise `RuntimeError`; generate valid request dicts
    - Assert `result["flags"]["requires_human_review"] is True`

- [x] 4. Checkpoint — unit-test the evaluator module
  - Ensure all tests pass, ask the user if questions arise.
  - Verify: valid request → all contract keys present; missing required field → `ValidationError`; `use_cache=False` → Qwen called every time; `emit_eval_usage` called with `route="sql_evaluation"`

- [x] 5. Add `/sql` route to `backend/model_app/api/routes/evaluation.py`
  - Import `SQLEvaluationRequest` from `backend.model_app.competencies.sql.eval_schema`
  - Import `get_sql_feedback` from `backend.model_app.evaluation.sql_evaluator`
  - Add `@router.post("/sql")` handler accepting `SQLEvaluationRequest` (Pydantic model, not `dict = Body(...)`) for free 422 validation
  - Call `bind_usage_meta_from_request(http_request)` once and pass result to `get_sql_feedback`
  - _Requirements: 1.1, 1.3, 1.4, 8.2_

  - [ ]* 5.1 Write property test for HTTP 422 on missing required fields — Property 1
    - **Property 1: Missing required fields yield 422**
    - **Validates: Requirements 1.3**
    - Use `hypothesis` to generate subsets of required fields `{question_id, question_description, user_query, reference_query, max_marks, schemas, test_result}` omitting at least one
    - POST each incomplete payload to `/api/v1/evaluation/sql` via FastAPI `TestClient`; assert HTTP 422

  - [ ]* 5.2 Write property test for HTTP 200 on valid requests — Property 2
    - **Property 2: Valid requests always return HTTP 200**
    - **Validates: Requirements 1.4**
    - Generate well-formed `SQLEvaluationRequest` dicts via `hypothesis`; mock `get_sql_feedback` to return a minimal valid dict
    - Assert HTTP 200 for every generated payload

  - [ ] 5.3 Write property test for caching round-trip — Property 4
    - **Property 4: Caching round-trip**
    - **Validates: Requirements 2.3**
    - Generate valid request with `use_cache=True`; submit twice; mock `_llm_chat_coder`
    - Assert Qwen mock called exactly once and both responses are identical

  - [ ]* 5.4 Write property test for full response contract — Property 8
    - **Property 8: Response always matches contract schema**
    - **Validates: Requirements 5.1**
    - Generate valid requests; assert response dict contains all top-level keys defined in `SQLAIFeedback` with correct types

- [x] 6. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Property tests use `hypothesis` (already in the project's test dependencies); each test runs ≥ 100 iterations
- Tag format for each property test: `# Feature: sql-evaluation, Property {N}: {property_text}`
- `_llm_chat_coder` and `emit_eval_usage` should be mocked via `unittest.mock.patch` in all property tests that exercise the full evaluator path
- `answer_log.expected_answer` must be forced to `""` in both the normalizer and the Qwen-call path — never trust Qwen to omit it
