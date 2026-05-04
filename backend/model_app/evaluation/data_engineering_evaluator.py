"""Data Engineering AI Evaluator — 3-layer scoring pipeline.

Flow:
  1. Deterministic Validation  (execution results from external engine + DataFrame comparison)
  2. Static Partial Credit     (pattern matching — only when execution fails)
  3. AI Review                 (Qwen Coder via vLLM — same as all other evaluators)

Final score = deterministic score overrides AI score (with exceptions).
Subjective questions use Rubric Scoring instead of Deterministic Validation.
"""
from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import time
from typing import Any

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────

_FALLBACK_REASONS = frozenset({
    "missing_execution_result",
    "missing_validation_result",
    "failed",
    "timeout",
    "cancelled",
    "pending",
    "running",
})

_EXECUTION_FAILURE_STATUSES = frozenset({
    "failed", "timeout", "cancelled", "pending", "running",
})

# ─────────────────────────────────────────────────────────────
# Part 1a: Cell normalisation and DataFrame comparison
# ─────────────────────────────────────────────────────────────

def _normalize_cell(value: Any) -> Any:
    """Normalise a cell value for order-agnostic DataFrame comparison.

    Rules:
    - None / NaN → None (treated as equal)
    - float with no fractional part → int (e.g. 3.0 → 3)
    - str → stripped of leading/trailing whitespace
    - bool → bool (must check before int/float since bool is subclass of int)
    """
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value):
            return None
        if value == int(value):
            return int(value)
        return value
    if isinstance(value, bool):
        return bool(value)
    if isinstance(value, str):
        return value.strip()
    return value


def _build_validation_signature(question: dict) -> str:
    """Build a deterministic string from expected output schema + row count across all test cases.
    Used as part of the Redis cache key for AI review responses.
    """
    parts = []
    for tc in question.get("test_cases", []):
        expected = tc.get("expected_output", [])
        cols = sorted(expected[0].keys()) if expected else []
        parts.append(f"{cols}:{len(expected)}")
    return "|".join(parts)


def _compare_dataframes(actual: list[dict], expected: list[dict]) -> dict:
    """Compare two DataFrames (as lists of row dicts) and return a score.

    Score caps:
    - Schema doesn't match → max 40
    - Schema matches, row count doesn't → max 60
    - Schema and row count match, data doesn't → max 85
    - All pass → 100

    Returns:
        {is_correct: bool, deterministic_score: float, score_reason: str}
    """
    # Handle empty expected output edge case
    if not expected:
        if not actual:
            return {"is_correct": True, "deterministic_score": 100.0, "score_reason": "exact_match"}
        return {"is_correct": False, "deterministic_score": 40.0, "score_reason": "schema_mismatch"}

    # ── Schema check ──────────────────────────────────────────
    expected_cols = sorted(expected[0].keys()) if expected else []
    actual_cols = sorted(actual[0].keys()) if actual else []

    if actual_cols != expected_cols:
        return {
            "is_correct": False,
            "deterministic_score": 40.0,
            "score_reason": "schema_mismatch",
        }

    # ── Row count check ───────────────────────────────────────
    if len(actual) != len(expected):
        return {
            "is_correct": False,
            "deterministic_score": 60.0,
            "score_reason": "row_count_mismatch",
        }

    # ── Data check (order-agnostic) ───────────────────────────
    def _row_key(row: dict) -> tuple:
        return tuple(_normalize_cell(row.get(c)) for c in expected_cols)

    actual_rows = sorted([_row_key(r) for r in actual])
    expected_rows = sorted([_row_key(r) for r in expected])

    if actual_rows != expected_rows:
        return {
            "is_correct": False,
            "deterministic_score": 85.0,
            "score_reason": "data_mismatch",
        }

    return {
        "is_correct": True,
        "deterministic_score": 100.0,
        "score_reason": "exact_match",
    }


def _run_deterministic_validation(question: dict, submission: dict) -> dict:
    """Use pre-computed execution results from the execution engine to score.

    The execution engine runs the candidate's PySpark code externally and sends
    back execution_results (status, output_df per test case). This function
    consumes those results and compares DataFrames against expected output.

    Returns:
        {
            deterministic_score: float,   # arithmetic mean of per-test-case scores
            per_test_case_results: list,
            score_reason: str,
            is_correct: bool,
        }
    """
    test_cases = question.get("test_cases", [])
    execution_results = submission.get("execution_results", [])

    if not test_cases:
        return {
            "deterministic_score": 0.0,
            "per_test_case_results": [],
            "score_reason": "missing_execution_result",
            "is_correct": False,
        }

    # Build a lookup from test_case_index → execution result
    exec_by_index: dict[int, dict] = {}
    for er in execution_results:
        idx = er.get("test_case_index", 0)
        exec_by_index[idx] = er

    per_test_case_results = []
    scores = []

    for idx, tc in enumerate(test_cases):
        exec_result = exec_by_index.get(idx, {})
        status = exec_result.get("status", "missing_execution_result")
        output_df = exec_result.get("output_df")
        expected = tc.get("expected_output", [])

        if status == "success" and output_df is not None:
            comparison = _compare_dataframes(output_df, expected)
            tc_score = comparison["deterministic_score"]
            tc_is_correct = comparison["is_correct"]
            tc_reason = comparison["score_reason"]
        else:
            tc_score = 0.0
            tc_is_correct = False
            tc_reason = status if status else "missing_execution_result"

        scores.append(tc_score)
        per_test_case_results.append({
            "test_case_index": idx,
            "status": status,
            "deterministic_score": tc_score,
            "is_correct": tc_is_correct,
            "score_reason": tc_reason,
            "error_message": exec_result.get("error_message"),
        })

    overall_score = sum(scores) / len(scores)

    # Determine overall reason from worst-case test case
    if all(r["is_correct"] for r in per_test_case_results):
        overall_reason = "exact_match"
        overall_correct = True
    elif any(r["score_reason"] in _EXECUTION_FAILURE_STATUSES for r in per_test_case_results):
        overall_reason = next(
            r["score_reason"] for r in per_test_case_results
            if r["score_reason"] in _EXECUTION_FAILURE_STATUSES
        )
        overall_correct = False
    elif any(r["score_reason"] == "missing_execution_result" for r in per_test_case_results):
        overall_reason = "missing_execution_result"
        overall_correct = False
    else:
        reason_priority = {"schema_mismatch": 0, "row_count_mismatch": 1, "data_mismatch": 2}
        worst = min(
            per_test_case_results,
            key=lambda r: reason_priority.get(r["score_reason"], 99),
        )
        overall_reason = worst["score_reason"]
        overall_correct = False

    return {
        "deterministic_score": overall_score,
        "per_test_case_results": per_test_case_results,
        "score_reason": overall_reason,
        "is_correct": overall_correct,
    }

# ─────────────────────────────────────────────────────────────
# Part 2: Static Partial Credit (fallback when execution fails)
# ─────────────────────────────────────────────────────────────

_PATTERNS: dict[str, str] = {
    "spark_session":   r"SparkSession|spark\.builder",
    "data_reading":    r"\.read\b|\.csv\b|\.parquet\b|\.json\b",
    "schema_cast":     r"\.schema\b|\.cast\b|StructType|StructField",
    "null_handling":   r"fillna|dropna|isNull",
    "transformations": r"withColumn|\.when\b|otherwise",
    "aggregations":    r"groupBy|\.agg\b|\.count\b|\.sum\b",
    "spark_sql":       r"spark\.sql|createOrReplaceTempView",
    "write_ops":       r"\.write\b|\.save\b|\.saveAsTable",
}

_PATTERN_POINTS = 3.0   # per matched pattern
_MAX_PATTERN_POINTS = 24.0
_RUBRIC_OVERLAP_POINTS = 0.6  # per matching token
_MAX_RUBRIC_OVERLAP_POINTS = 12.0
_MAX_STATIC_SCORE = 40.0


def _tokenize(text: str) -> set[str]:
    """Extract lowercase alphanumeric tokens from text."""
    return set(re.findall(r"[a-zA-Z_]\w*", text.lower()))


def _run_static_partial_credit(question: dict, submission: dict) -> float:
    """Award partial credit based on code patterns when execution fails.

    Scoring (max 40 pts total):
    - Pattern hits (max 24 pts): 3 pts each for 8 PySpark patterns
    - Rubric token overlap (max 12 pts): 0.6 pts per matching token
    - Code length bonus (max 4 pts): 40+ unique tokens=4pts, 20+=2pts, else 0

    Only called when execution status is in _EXECUTION_FAILURE_STATUSES.
    """
    code = submission.get("code", "")
    if not code.strip():
        return 0.0

    # ── Pattern hit points ────────────────────────────────────
    pattern_score = 0.0
    for pattern_re in _PATTERNS.values():
        if re.search(pattern_re, code):
            pattern_score += _PATTERN_POINTS
    pattern_score = min(pattern_score, _MAX_PATTERN_POINTS)

    # ── Rubric token overlap ──────────────────────────────────
    title = question.get("title", "")
    description = question.get("description", "")
    rubric_tokens = _tokenize(f"{title} {description}")
    code_tokens = _tokenize(code)

    overlap_count = len(rubric_tokens & code_tokens)
    rubric_score = min(overlap_count * _RUBRIC_OVERLAP_POINTS, _MAX_RUBRIC_OVERLAP_POINTS)

    # ── Code length bonus ─────────────────────────────────────
    unique_token_count = len(code_tokens)
    if unique_token_count >= 40:
        length_bonus = 4.0
    elif unique_token_count >= 20:
        length_bonus = 2.0
    else:
        length_bonus = 0.0

    total = pattern_score + rubric_score + length_bonus
    return min(total, _MAX_STATIC_SCORE)


# ─────────────────────────────────────────────────────────────
# Part 3: Subjective Rubric Scoring
# ─────────────────────────────────────────────────────────────

_REASONING_TERMS = frozenset({
    "because", "tradeoff", "latency", "throughput", "schema", "quality",
    "monitoring", "partitioning", "checkpoint", "deduplicate", "watermark",
    "backfill", "rollback", "governance", "lineage",
})

_SENTENCE_SPLIT = re.compile(r"[.!?]+")


def _token_overlap_ratio(a_tokens: set[str], b_tokens: set[str]) -> float:
    """Jaccard-style overlap: |a ∩ b| / |a| (fraction of a covered by b)."""
    if not a_tokens:
        return 0.0
    return len(a_tokens & b_tokens) / len(a_tokens)


def _run_subjective_rubric(question: dict, submission: dict) -> float:
    """Deterministic rubric scoring for subjective answers (max 100 pts).

    Components:
    - Coverage score  (55 pts max): rubric items with ≥50% token overlap
    - Concept score   (15 pts max): rubric vocabulary present in answer
    - Depth score     (15 pts max): word count / 180
    - Structure score (10 pts max): sentence count
    - Reasoning score (10 pts max): reasoning terms found

    Penalties applied in order: word count → copy-paste → coverage ratio.
    """
    answer = submission.get("answer", "")
    rubric_items = question.get("rubric_items", [])

    answer_tokens = _tokenize(answer)
    answer_words = answer.split()
    word_count = len(answer_words)

    # ── Coverage score (55 pts) ───────────────────────────────
    if rubric_items:
        covered = sum(
            1 for item in rubric_items
            if _token_overlap_ratio(_tokenize(item), answer_tokens) >= 0.50
        )
        coverage_ratio = covered / len(rubric_items)
        coverage_score = coverage_ratio * 55.0
    else:
        coverage_ratio = 0.0
        coverage_score = 0.0

    # ── Concept score (15 pts) ────────────────────────────────
    rubric_vocab: set[str] = set()
    for item in rubric_items:
        rubric_vocab |= _tokenize(item)
    if rubric_vocab:
        concept_score = (len(rubric_vocab & answer_tokens) / len(rubric_vocab)) * 15.0
    else:
        concept_score = 0.0

    # ── Depth score (15 pts) ──────────────────────────────────
    depth_score = min(word_count / 180.0, 1.0) * 15.0

    # ── Structure score (10 pts) ──────────────────────────────
    sentences = [s.strip() for s in _SENTENCE_SPLIT.split(answer) if s.strip()]
    sentence_count = len(sentences)
    if sentence_count >= 4:
        structure_score = 10.0
    elif sentence_count >= 2:
        structure_score = 7.0
    else:
        structure_score = 3.0

    # ── Reasoning score (10 pts) ──────────────────────────────
    answer_lower = answer.lower()
    reasoning_hits = sum(1 for term in _REASONING_TERMS if term in answer_lower)
    reasoning_score = min(reasoning_hits * 2.5, 10.0)

    total = coverage_score + concept_score + depth_score + structure_score + reasoning_score

    # ── Word count penalties ──────────────────────────────────
    if word_count < 20:
        total = min(total, 10.0)
    elif word_count < 40:
        total = total * 0.45
    elif word_count < 70:
        total = total * 0.70

    # ── Copy-paste detection ──────────────────────────────────
    question_text = f"{question.get('title', '')} {question.get('description', '')}"
    question_tokens = _tokenize(question_text)
    if question_tokens and answer_tokens:
        similarity = len(question_tokens & answer_tokens) / len(question_tokens)
        novel_ratio = len(answer_tokens - question_tokens) / len(answer_tokens) if answer_tokens else 1.0
        if similarity >= 0.88 and novel_ratio < 0.25:
            total = min(total, 8.0)
        elif similarity >= 0.75 and novel_ratio < 0.35:
            total = min(total, 22.0)

    # ── Coverage ratio penalty ────────────────────────────────
    if coverage_ratio < 0.25:
        total = min(total, 35.0)

    return max(0.0, min(total, 100.0))


# ─────────────────────────────────────────────────────────────
# Part 4: AI Review (Qwen Coder via vLLM — same as all other evaluators)
# ─────────────────────────────────────────────────────────────

_AI_SYSTEM_PROMPT = """You are a strict Data Engineering evaluator. Return ONLY minified JSON — no markdown, no code fences, no explanation.

Output schema (all keys required):
{"overall_score":<float 0-100>,"correctness_feedback":"<1-2 sentences>","performance_feedback":"<1-2 sentences>","best_practices_feedback":"<1-2 sentences>","improvement_suggestions":["<string>"],"strengths":["<string>"],"areas_for_improvement":["<string>"],"code_examples":[],"alternative_approaches":[]}

Rules:
- overall_score must be 0-100.
- Max 3 items per list field.
- Keep each string under 150 characters.
- Output must end with } and contain nothing after it."""

_EMPTY_AI_FEEDBACK: dict = {
    "overall_score": None,
    "correctness_feedback": "",
    "performance_feedback": "",
    "best_practices_feedback": "",
    "improvement_suggestions": [],
    "strengths": [],
    "areas_for_improvement": [],
    "code_examples": [],
    "alternative_approaches": [],
}

# In-process TTL cache (1 hour) — same pattern as all other evaluators
from cachetools import TTLCache as _TTLCache
_ai_cache: _TTLCache = _TTLCache(maxsize=500, ttl=3600)


def _build_coding_prompt(question: dict, submission: dict, det_results: dict) -> str:
    title = question.get("title", "")
    description = str(question.get("description", ""))[:400]
    code = str(submission.get("code", ""))[:800]
    exec_status = det_results.get("score_reason", "unknown")
    per_tc = det_results.get("per_test_case_results", [])
    passed = sum(1 for r in per_tc if r.get("is_correct"))
    total = len(per_tc)

    return (
        f"question: {title}\n"
        f"description: {description}\n"
        f"difficulty: {question.get('difficulty', 'medium')}\n\n"
        f"execution_status: {exec_status}\n"
        f"test_results: {passed}/{total} passed\n\n"
        f"candidate_code:\n```python\n{code}\n```\n\n"
        "Evaluate the PySpark code. Return ONLY the JSON described in the system prompt."
    )


def _build_subjective_prompt(question: dict, submission: dict) -> str:
    title = question.get("title", "")
    description = str(question.get("description", ""))[:400]
    rubric_items = question.get("rubric_items", [])[:6]
    answer = str(submission.get("answer", ""))[:800]

    return (
        f"question: {title}\n"
        f"description: {description}\n"
        f"rubric_items: {rubric_items}\n\n"
        f"candidate_answer:\n{answer}\n\n"
        "Evaluate the written answer. Return ONLY the JSON described in the system prompt."
    )


def _run_ai_review(
    question: dict,
    submission: dict,
    det_results: dict,
    use_cache: bool,
) -> dict:
    """Call Qwen Coder (vLLM) for qualitative feedback — same pattern as all other evaluators.

    Uses in-process TTLCache (1h). Returns _EMPTY_AI_FEEDBACK on any failure.
    """
    from backend.model_app.evaluation.base import _llm_chat_coder, safe_parse

    question_id = question.get("id", "")
    question_type = question.get("question_type", "coding")
    code_or_answer = submission.get("code", "") or submission.get("answer", "")

    # Cache key — MD5 of content (same as other evaluators)
    cache_key = hashlib.md5(
        f"{question_id}:{code_or_answer[:500]}".encode()
    ).hexdigest()

    if use_cache and cache_key in _ai_cache:
        logger.info("[DE_EVAL] AI cache hit question_id=%s", question_id)
        return _ai_cache[cache_key]

    # Build prompt
    if question_type == "coding":
        user_prompt = _build_coding_prompt(question, submission, det_results)
    else:
        user_prompt = _build_subjective_prompt(question, submission)

    messages = [
        {"role": "system", "content": _AI_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.1, max_tokens=600)
        parsed = safe_parse(raw)

        if parsed.get("parse_error"):
            raise ValueError(f"safe_parse error: {parsed.get('overall_summary', '')[:200]}")

        def _str(v, n=200): return str(v)[:n] if v is not None else ""
        def _lst(v): return [str(x) for x in (v or [])[:3] if str(x).strip()]
        def _flt(v):
            try: return max(0.0, min(100.0, float(v)))
            except Exception: return 0.0

        result = {
            "overall_score": _flt(parsed.get("overall_score")),
            "correctness_feedback": _str(parsed.get("correctness_feedback")),
            "performance_feedback": _str(parsed.get("performance_feedback")),
            "best_practices_feedback": _str(parsed.get("best_practices_feedback")),
            "improvement_suggestions": _lst(parsed.get("improvement_suggestions")),
            "strengths": _lst(parsed.get("strengths")),
            "areas_for_improvement": _lst(parsed.get("areas_for_improvement")),
            "code_examples": _lst(parsed.get("code_examples")),
            "alternative_approaches": _lst(parsed.get("alternative_approaches")),
        }

    except Exception as exc:
        logger.warning("[DE_EVAL] Qwen AI review failed question_id=%s: %s", question_id, exc)
        return dict(_EMPTY_AI_FEEDBACK)

    _ai_cache[cache_key] = result
    return result


# ─────────────────────────────────────────────────────────────
# Part 5: Final Score Resolution
# ─────────────────────────────────────────────────────────────

def _resolve_final_score(
    det_score: float,
    static_score: float,
    ai_score: float | None,
    reason: str,
) -> tuple[float, str]:
    """Combine the three scoring layers into a single final score.

    Resolution rules (in priority order):
    1. Default: final_score = det_score
    2. AI fallback: if reason ∈ FALLBACK_REASONS AND det_score == 0 AND ai_score is not None
       → final_score = ai_score
    3. Static override: if static_score > ai_score (and ai_score is not None)
       → final_score = static_score

    Always clamps to [0, 100].
    """
    resolved_reason = reason or "deterministic"
    final = det_score

    # Rule 2: AI fallback when deterministic had nothing to say
    if reason in _FALLBACK_REASONS and det_score == 0 and ai_score is not None:
        final = ai_score
        resolved_reason = f"ai_fallback:{reason}"

    # Rule 3: Static override when static beats AI
    if ai_score is not None and static_score > ai_score:
        final = static_score
        resolved_reason = "static_partial_credit"

    final = max(0.0, min(100.0, final))
    return final, resolved_reason or "deterministic"


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_data_engineering_feedback(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """Main entry point called by the route handler.

    Accepts raw dict payload (validated by Pydantic at route level).
    Returns a DataEngineeringEvalResponse-compatible dict.

    Coding path:
      1. _run_deterministic_validation (sandbox + DataFrame comparison)
      2. _run_static_partial_credit    (if any test case failed/timed out)
      3. _run_ai_review
      4. _resolve_final_score

    Subjective path:
      1. _run_subjective_rubric        (stored as static_partial_score)
      2. _run_ai_review
      3. _resolve_final_score          (det_score=0, reason="missing_execution_result")
    """
    from backend.model_app.evaluation.base import emit_eval_usage

    question = payload.get("question") or {}
    submission = payload.get("submission") or {}
    use_cache = bool(payload.get("use_cache", True))
    question_type = question.get("question_type", "coding")

    t_start = time.time()
    ai_cache_hit = False

    # ── Coding path ───────────────────────────────────────────
    if question_type == "coding":
        det_result = _run_deterministic_validation(question, submission)
        deterministic_score = det_result["deterministic_score"]
        per_test_case_results = det_result["per_test_case_results"]
        score_reason = det_result["score_reason"]
        is_correct = det_result["is_correct"]

        # Static partial credit only when execution failed
        execution_failed = any(
            r.get("score_reason") in _EXECUTION_FAILURE_STATUSES
            for r in per_test_case_results
        ) or score_reason in _EXECUTION_FAILURE_STATUSES

        static_partial_score = (
            _run_static_partial_credit(question, submission)
            if execution_failed
            else 0.0
        )

    # ── Subjective path ───────────────────────────────────────
    else:
        deterministic_score = 0.0
        per_test_case_results = []
        score_reason = "missing_execution_result"
        is_correct = False
        static_partial_score = _run_subjective_rubric(question, submission)

    # ── AI review (both paths) ────────────────────────────────
    det_results_for_ai = {
        "per_test_case_results": per_test_case_results,
        "score_reason": score_reason,
    }

    ai_error: str | None = None
    try:
        # Check in-process cache before calling Qwen
        from backend.model_app.evaluation.data_engineering_evaluator import _ai_cache
        code_or_answer = submission.get("code", "") or submission.get("answer", "")
        question_id = question.get("id", "")
        _ck = hashlib.md5(f"{question_id}:{code_or_answer[:500]}".encode()).hexdigest()
        if use_cache and _ck in _ai_cache:
            ai_cache_hit = True

        ai_feedback = _run_ai_review(question, submission, det_results_for_ai, use_cache)
        ai_score: float | None = ai_feedback.get("overall_score")
    except Exception as exc:
        logger.warning("[DE_EVAL] AI review failed: %s", exc)
        ai_feedback = dict(_EMPTY_AI_FEEDBACK)
        ai_score = None
        ai_error = str(exc)

    # ── Score resolution ──────────────────────────────────────
    final_score, resolved_reason = _resolve_final_score(
        det_score=deterministic_score,
        static_score=static_partial_score,
        ai_score=ai_score,
        reason=score_reason,
    )

    overall_score = final_score

    latency_ms = (time.time() - t_start) * 1000
    if ai_error:
        emit_eval_usage(
            usage_meta,
            "data_engineering_evaluation",
            latency_ms=latency_ms,
            status="error",
            error_detail=ai_error,
        )
    else:
        emit_eval_usage(
            usage_meta,
            "data_engineering_evaluation",
            latency_ms=latency_ms,
            cache_hit=ai_cache_hit,
        )

    return {
        "overall_score": overall_score,
        "deterministic_score": deterministic_score,
        "static_partial_score": static_partial_score,
        "ai_score": ai_score,
        "final_score": final_score,
        "score_reason": resolved_reason,
        "per_test_case_results": per_test_case_results,
        "ai_feedback": ai_feedback,
        "is_correct": is_correct,
    }
