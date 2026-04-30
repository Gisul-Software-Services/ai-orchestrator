# Implementation Plan: DevOps / Cloud Evaluation

## Overview

Add two new evaluation endpoints (`/api/v1/evaluation/devops` and `/api/v1/evaluation/cloud`) that replace Aaptor's OpenAI-based evaluators with Qwen-based equivalents. The implementation follows the established `sql_evaluator.py` pattern: TTLCache, `safe_parse`, `emit_eval_usage`, and a deterministic fallback. The Cloud evaluator is a thin wrapper that delegates entirely to the DevOps evaluator.

## Tasks

- [x] 1. Create Pydantic request models
  - Create `backend/model_app/competencies/devops/eval_schema.py`
  - Define `EngineResponse`, `ValidationSignals`, `TerminalHistoryEntry`, `DevOpsQuestion`, `DevOpsSubmission`, `DevOpsEvalRequest`, and `CloudEvalRequest` models exactly as specified in the design
  - All fields must have the correct types, defaults, and `Field(default_factory=list)` for list fields
  - _Requirements: 1.3, 1.4, 1.5, 2.1_

- [x] 2. Implement the DevOps evaluator core
  - Create `backend/model_app/evaluation/devops_evaluator.py`
  - [x] 2.1 Implement helper functions: `_cache_key`, `_empty_response`, `_compute_scores`, `_detect_mode`
    - `_cache_key`: MD5 of `question_id + json.dumps(submission, sort_keys=True, default=str)`
    - `_empty_response`: returns the full `ai_feedback` dict with all required keys and safe defaults
    - `_compute_scores`: scoring formula — `round((completed/total)*100)`, per-task score, returns `(overall_score, completed, total)`
    - `_detect_mode`: returns `"terminal"` when `terminal_history` is non-empty list or `engine_response.exit_code` is not None; else `"scenario"`
    - _Requirements: 3.1, 3.2, 3.3, 6.1, 7.1, 7.2, 7.3, 8.2_

  - [ ]* 2.2 Write property test for `_compute_scores` (Property 3)
    - **Property 3: Scoring formula correctness**
    - Generate lists of 0–10 task dicts with random `completed` booleans; assert `overall_score == round((completed/total)*100)` (0 when total==0), per-task scores match formula
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

  - [ ]* 2.3 Write property test for `_detect_mode` (Property 4)
    - **Property 4: Mode detection correctness**
    - Generate submission dicts with varying `terminal_history` and `engine_response`; assert return value matches the specification
    - **Validates: Requirements 3.1, 3.2, 3.3**

  - [x] 2.4 Implement prompt builders: `_build_terminal_user_prompt` and `_build_scenario_user_prompt`
    - Terminal prompt: includes question fields, last 10 terminal history entries (output capped at 300 chars), engine_response, validation_signals
    - Scenario prompt: includes question fields, answer (capped at 1500 chars), validation_signals
    - Both prompts cap field lengths as specified in the design to stay within the 1024-token context budget
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.1, 5.2, 5.3_

  - [x] 2.5 Implement `_normalize_response` and `_fallback_response`
    - `_normalize_response`: maps Qwen's raw output to the full `ai_feedback` contract; never raises; uses `_compute_scores` for scoring; substitutes safe defaults for all missing fields
    - `_fallback_response`: sets `overall_score` from `validation_signals.question_score` if available else 0; sets `feedback_summary` to `"Automated scoring applied. Human review recommended."`; sets all score fields to 0 and list fields to empty lists
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 9.1, 9.2, 9.3, 9.4_

  - [ ]* 2.6 Write property test for `_normalize_response` (Property 2)
    - **Property 2: Normalization never raises**
    - Generate arbitrary dicts using `hypothesis.strategies.dictionaries`; call `_normalize_response(raw, validation_signals=None)` directly; assert no exception raised and result is a dict with all required keys
    - **Validates: Requirements 6.6**

  - [x] 2.7 Implement `get_devops_feedback` entry point
    - TTLCache `TTLCache(maxsize=500, ttl=3600)` at module level
    - Cache lookup using `_cache_key`; return cached result and call `emit_eval_usage(cache_hit=True)` on hit
    - Short-circuit on empty submission (no answer and no terminal history): return `_empty_response()` without calling LLM
    - Detect mode, build appropriate prompt, call `_llm_chat_coder(messages, max_tokens=900)`, call `safe_parse`, call `_normalize_response`
    - Catch all exceptions: log at WARNING, call `emit_eval_usage(status="error")`, return `_fallback_response`
    - `route` parameter defaults to `"devops_evaluation"` and is passed to all `emit_eval_usage` calls
    - Store result in cache after successful LLM call
    - _Requirements: 1.1, 1.2, 1.6, 4.1, 5.1, 8.1, 8.3, 8.4, 9.1, 10.1, 10.2, 10.3_

  - [ ]* 2.8 Write property test for `get_devops_feedback` — response contract completeness (Property 1)
    - **Property 1: Response contract completeness**
    - Generate random `DevOpsEvalRequest`-shaped dicts; mock `_llm_chat_coder` to return a valid JSON string with a random subset of fields; assert all required keys present, correct types, `ai_generated == True`
    - **Validates: Requirements 1.2, 1.6, 6.1, 6.2, 6.3, 6.4, 6.5**

  - [ ]* 2.9 Write property test for `get_devops_feedback` — fallback on LLM failure (Property 6)
    - **Property 6: Fallback on LLM failure**
    - Generate random valid payloads; mock `_llm_chat_coder` to raise a random exception from `{ValueError, RuntimeError, TimeoutError, OSError}`; assert no exception raised and result is a dict with all required keys
    - **Validates: Requirements 9.1**

- [ ] 3. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 4. Implement the Cloud evaluator wrapper
  - Create `backend/model_app/evaluation/cloud_evaluator.py`
  - Implement `get_cloud_feedback` as a thin wrapper: import `get_devops_feedback` and call it with `route="cloud_evaluation"`, passing `payload` and `usage_meta` unchanged
  - No independent scoring logic
  - _Requirements: 2.2, 2.3, 10.4_

  - [ ]* 4.1 Write property test for Cloud evaluator delegation (Property 5)
    - **Property 5: Cloud evaluator delegation**
    - Generate random valid payloads; mock `get_devops_feedback` to record calls and return a fixed result; call `get_cloud_feedback(payload)`; assert `get_devops_feedback` was called exactly once with `route="cloud_evaluation"` and the same payload
    - **Validates: Requirements 2.2, 2.3**

- [x] 5. Add route handlers to the evaluation router
  - Edit `backend/model_app/api/routes/evaluation.py`
  - Add imports for `DevOpsEvalRequest`, `CloudEvalRequest` from `backend.model_app.competencies.devops.eval_schema`
  - Add imports for `get_devops_feedback` and `get_cloud_feedback`
  - Add `POST /devops` handler: extract `usage_meta` via `bind_usage_meta_from_request`, call `get_devops_feedback(payload=payload.model_dump(), usage_meta=usage_meta)`
  - Add `POST /cloud` handler: extract `usage_meta` via `bind_usage_meta_from_request`, call `get_cloud_feedback(payload=payload.model_dump(), usage_meta=usage_meta)`
  - _Requirements: 1.1, 2.1_

- [x] 6. Add org-gating paths to the gateway
  - Edit `backend/gateway/main.py`
  - Add `"/api/v1/evaluation/devops"` and `"/api/v1/evaluation/cloud"` to `_ORG_GATED_POST_PATHS`
  - _Requirements: (gateway org-gating, consistent with all other evaluation endpoints)_

- [x] 7. Create frontend proxy routes
  - Create `frontend/web/app/api/admin/evaluate/devops/route.ts` with `export const POST = makeAdminProxyPost("/api/v1/evaluation/devops");`
  - Create `frontend/web/app/api/admin/evaluate/cloud/route.ts` with `export const POST = makeAdminProxyPost("/api/v1/evaluation/cloud");`
  - _Requirements: 11.1, 11.2_

- [x] 8. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- The Cloud evaluator (task 4) must be implemented after the DevOps evaluator (task 2) since it imports from it
- Route handlers (task 5) depend on both evaluators and the Pydantic models (tasks 1, 2, 4)
- Property tests use [Hypothesis](https://hypothesis.readthedocs.io/) with a minimum of 100 iterations per property
- The design document contains the exact code for all components — use it as the authoritative reference during implementation
