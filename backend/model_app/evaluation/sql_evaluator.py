"""SQL AI Evaluator — Production Level.

Flow:
  1. Parse and compare user_output vs expected_output (structured comparison)
  2. Compute deterministic correctness score from execution result
  3. Check cache
  4. Short-circuit on empty/trivial queries
  5. Call Qwen with rich structured context
  6. Normalize + enforce score floor/cap
  7. Store in cache, emit billing usage
  8. Fallback to deterministic score on any failure
"""
from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

_CRITERIA_WEIGHTS: dict[str, float] = {
    "correctness":          0.40,
    "efficiency":           0.25,
    "best_practices":       0.15,
    "edge_cases":           0.10,
    "alternative_solutions": 0.10,
}

_VALID_RISK_VALUES = {"Low", "Medium", "High"}

_SYSTEM_PROMPT = """You are a strict SQL query evaluator. Return ONLY minified JSON — no markdown, no code fences, no extra text.

Output schema (all keys required):
{"score":<float 0-max_marks>,"criteria_scores":{"correctness":{"score":<float>,"weight":0.40,"feedback":"<1 sentence>"},"efficiency":{"score":<float>,"weight":0.25,"feedback":"<1 sentence>"},"best_practices":{"score":<float>,"weight":0.15,"feedback":"<1 sentence>"},"edge_cases":{"score":<float>,"weight":0.10,"feedback":"<1 sentence>"},"alternative_solutions":{"score":<float>,"weight":0.10,"feedback":"<1 sentence>"}},"feedback":{"summary":"<2 sentences>","strengths":["<string>"],"weaknesses":["<string>"],"suggestions":["<string>"]},"flags":{"plagiarism_risk":"Low","ai_generated_risk":"Low","confidence_level":<float 0-1>}}

Evaluation criteria:
- correctness (40%): Does the result set match expected output? Use the EXECUTION RESULT section as ground truth.
- efficiency (25%): SQL-specific terms only — "full table scan", "index seek", "hash join", "N+1 query", "subquery vs JOIN"
- best_practices (15%): proper aliases, no SELECT *, meaningful column names, correct JOIN type
- edge_cases (10%): NULL handling, empty result handling, boundary conditions, type casting
- alternative_solutions (10%): could CTEs, window functions, or set operations improve this?

Score floor/cap (HARD RULES — do not violate):
- execution passed=true: correctness score >= 80% of its max weight
- execution passed=false: correctness score <= 30% of its max weight

Rules:
- Max 2 items per list.
- Keep each string under 120 characters.
- Output must end with } and contain nothing after it.
- Base correctness ONLY on the execution result, not your own SQL analysis."""


# ─────────────────────────────────────────────────────────────
# Output comparison helpers
# ─────────────────────────────────────────────────────────────

def _parse_output(raw: Any) -> list:
    """Parse user_output or expected_output to a list of rows."""
    if not raw:
        return []
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        raw = raw.strip()
        if not raw or raw.lower() in ("none", "null", "[]", ""):
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return parsed
            return [parsed]
        except Exception:
            return []
    return []


def _compare_outputs(user_rows: list, expected_rows: list, order_sensitive: bool = False) -> dict:
    """
    Structured comparison of user output vs expected output.
    Returns a dict with comparison metrics used in the prompt and for partial credit.
    """
    user_count = len(user_rows)
    expected_count = len(expected_rows)

    if not expected_rows:
        return {
            "rows_match": user_count == 0,
            "user_row_count": user_count,
            "expected_row_count": 0,
            "row_count_match": user_count == 0,
            "column_match": True,
            "partial_match_ratio": 1.0 if user_count == 0 else 0.0,
            "sample_user": [],
            "sample_expected": [],
            "note": "No expected output — query may return empty result set",
        }

    # Column comparison
    user_cols = set()
    expected_cols = set()
    if user_rows and isinstance(user_rows[0], dict):
        user_cols = set(user_rows[0].keys())
    if expected_rows and isinstance(expected_rows[0], dict):
        expected_cols = set(expected_rows[0].keys())

    col_match = user_cols == expected_cols if (user_cols and expected_cols) else True

    # Row matching — convert rows to comparable tuples
    def _row_to_tuple(row):
        if isinstance(row, dict):
            return tuple(str(v) for v in sorted(row.values(), key=str))
        if isinstance(row, (list, tuple)):
            return tuple(str(v) for v in row)
        return (str(row),)

    user_tuples = [_row_to_tuple(r) for r in user_rows]
    expected_tuples = [_row_to_tuple(r) for r in expected_rows]

    if order_sensitive:
        exact_match = user_tuples == expected_tuples
        matched = sum(1 for u, e in zip(user_tuples, expected_tuples) if u == e)
    else:
        # Order-insensitive: compare as multisets
        from collections import Counter
        user_counter = Counter(user_tuples)
        expected_counter = Counter(expected_tuples)
        exact_match = user_counter == expected_counter
        # Count matching rows
        matched = sum(min(user_counter[t], expected_counter[t]) for t in expected_counter)

    partial_ratio = round(matched / max(expected_count, 1), 3)
    rows_match = exact_match and user_count == expected_count

    return {
        "rows_match": rows_match,
        "user_row_count": user_count,
        "expected_row_count": expected_count,
        "row_count_match": user_count == expected_count,
        "column_match": col_match,
        "matched_rows": matched,
        "partial_match_ratio": partial_ratio,
        "sample_user": user_rows[:3],
        "sample_expected": expected_rows[:3],
        "order_sensitive": order_sensitive,
    }


def _compute_partial_credit(comparison: dict, passed: bool, max_marks: float) -> float:
    """
    Compute a deterministic correctness score based on execution result.
    This is the ground truth — LLM cannot override this.

    passed=True  → correctness >= 80% of correctness weight
    passed=False → partial credit based on how close the output is
    """
    correctness_max = max_marks * _CRITERIA_WEIGHTS["correctness"]

    if passed:
        # Full credit for passing
        return correctness_max

    # Partial credit for failing — based on how close the output is
    ratio = comparison.get("partial_match_ratio", 0.0)
    row_count_match = comparison.get("row_count_match", False)
    col_match = comparison.get("column_match", True)

    # Base partial credit
    partial = ratio * 0.5  # max 50% of correctness weight for partial match

    # Bonus for correct structure
    if col_match:
        partial += 0.1
    if row_count_match:
        partial += 0.1

    # Cap at 30% of correctness weight for failed execution
    partial = min(partial, 0.30)

    return round(correctness_max * partial, 4)


# ─────────────────────────────────────────────────────────────
# User prompt construction
# ─────────────────────────────────────────────────────────────

def _build_user_prompt(req: dict, comparison: dict, deterministic_correctness: float) -> str:
    desc = (req.get("question_description") or "")[:400]
    user_q = req.get("user_query") or ""
    ref_q = (req.get("reference_query") or "")[:300]
    schemas_str = json.dumps(req.get("schemas") or {})[:400]
    tr = req.get("test_result") or {}
    passed = bool(tr.get("passed", False))
    error = (tr.get("error") or "")[:200]
    max_marks = float(req.get("max_marks") or 1.0)
    correctness_max = max_marks * _CRITERIA_WEIGHTS["correctness"]

    # Format comparison for prompt
    comp_str = (
        f"  execution_passed: {passed}\n"
        f"  user_rows: {comparison['user_row_count']}\n"
        f"  expected_rows: {comparison['expected_row_count']}\n"
        f"  row_count_match: {comparison['row_count_match']}\n"
        f"  column_match: {comparison['column_match']}\n"
        f"  partial_match_ratio: {comparison['partial_match_ratio']}\n"
        f"  sample_user_output: {json.dumps(comparison['sample_user'])[:300]}\n"
        f"  sample_expected_output: {json.dumps(comparison['sample_expected'])[:300]}"
    )
    if error:
        comp_str += f"\n  execution_error: {error}"

    return (
        f"question: {desc}\n"
        f"difficulty: {req.get('difficulty', 'medium')}\n"
        f"max_marks: {max_marks}\n"
        f"order_sensitive: {req.get('order_sensitive', False)}\n\n"
        f"schemas: {schemas_str}\n\n"
        f"candidate_query:\n{user_q}\n\n"
        f"reference_query (for context only — do not reveal to candidate):\n{ref_q}\n\n"
        f"EXECUTION RESULT (ground truth — base correctness score on this):\n{comp_str}\n\n"
        f"IMPORTANT: correctness score is already determined by execution.\n"
        f"  Set correctness.score = {round(deterministic_correctness, 4)} (deterministic, do not change).\n"
        f"  correctness.score max = {round(correctness_max, 4)}\n\n"
        f"Evaluate efficiency, best_practices, edge_cases, alternative_solutions based on the query.\n"
        f"Return ONLY the JSON described in the system prompt."
    )


# ─────────────────────────────────────────────────────────────
# Empty / default response builders
# ─────────────────────────────────────────────────────────────

def _empty_response_dict() -> dict:
    criteria: dict = {
        k: {"score": 0.0, "weight": w, "feedback": ""}
        for k, w in _CRITERIA_WEIGHTS.items()
    }
    return {
        "question_id": "",
        "section": "",
        "question_type": "SQL",
        "overall_score": 0,
        "score": 0.0,
        "max_marks": 0.0,
        "percentage": 0.0,
        "criteria_scores": criteria,
        "feedback": {
            "summary": "",
            "strengths": [],
            "weaknesses": [],
            "detailed_analysis": "",
            "suggestions": [],
        },
        "answer_log": {
            "submitted_answer": "",
            "expected_answer": "",
            "key_points_covered": [],
            "key_points_missed": [],
            "incorrect_points": [],
            "partial_credit_reasoning": "",
        },
        "areas_of_improvement": [],
        "benchmarking": {
            "compared_to_peers": "",
            "percentile": 0.0,
            "industry_standard": "",
        },
        "insights": {
            "approach_quality": "",
            "edge_case_handling": "",
            "alternative_solutions": [],
        },
        "flags": {
            "plagiarism_risk": "Low",
            "ai_generated_risk": "Low",
            "incomplete_answer": False,
            "requires_human_review": False,
            "confidence_level": 0.0,
        },
        "evaluation_version": "2.2.0",
        "ai_generated": True,
    }


def _empty_response(req: dict) -> dict:
    base = _empty_response_dict()
    base["question_id"] = req.get("question_id") or ""
    base["section"] = req.get("section") or ""
    base["max_marks"] = float(req.get("max_marks") or 0)
    base["answer_log"]["submitted_answer"] = req.get("user_query") or ""
    base["answer_log"]["expected_answer"] = req.get("reference_query") or ""
    base["flags"]["incomplete_answer"] = True
    return base


# ─────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────

def _normalize_product(raw: dict, max_marks: float, deterministic_correctness: float) -> dict:
    """Normalize Qwen output to full contract schema. Enforce deterministic correctness."""
    base = _empty_response_dict()

    if not isinstance(raw, dict):
        return base

    if raw.get("parse_error") is True:
        summary = str(raw.get("overall_summary") or "").strip()[:800]
        if summary:
            base["feedback"]["summary"] = summary
        return base

    def _to_float(v, default: float = 0.0) -> float:
        try:
            if isinstance(v, bool):
                return default
            return float(v)
        except Exception:
            return default

    def _clamp(v: float, lo: float, hi: float) -> float:
        return lo if v < lo else hi if v > hi else v

    def _to_str(v) -> str:
        return str(v) if v is not None else ""

    def _to_list_of_str(v) -> list:
        if isinstance(v, list):
            return [str(x) for x in v if str(x).strip()]
        return []

    # score
    base["score"] = _clamp(_to_float(raw.get("score"), 0.0), 0.0, max_marks)

    # criteria_scores — normalize LLM output but OVERRIDE correctness with deterministic value
    raw_criteria = raw.get("criteria_scores") or {}
    if isinstance(raw_criteria, dict):
        for k, w in _CRITERIA_WEIGHTS.items():
            raw_c = raw_criteria.get(k) or {}
            if isinstance(raw_c, dict):
                if k == "correctness":
                    # Always use deterministic correctness — LLM cannot override
                    c_score = deterministic_correctness
                else:
                    c_score = _clamp(_to_float(raw_c.get("score"), 0.0), 0.0, max_marks * w)
                base["criteria_scores"][k] = {
                    "score": c_score,
                    "weight": w,
                    "feedback": _to_str(raw_c.get("feedback")),
                }
    else:
        # No criteria from LLM — set correctness deterministically
        base["criteria_scores"]["correctness"]["score"] = deterministic_correctness

    # feedback
    raw_fb = raw.get("feedback") or {}
    if isinstance(raw_fb, dict):
        base["feedback"]["summary"] = _to_str(raw_fb.get("summary"))
        base["feedback"]["strengths"] = _to_list_of_str(raw_fb.get("strengths"))
        base["feedback"]["weaknesses"] = _to_list_of_str(raw_fb.get("weaknesses"))
        base["feedback"]["suggestions"] = _to_list_of_str(raw_fb.get("suggestions"))

    # flags
    raw_flags = raw.get("flags") or {}
    if isinstance(raw_flags, dict):
        risk_val = str(raw_flags.get("plagiarism_risk") or "Low")
        base["flags"]["plagiarism_risk"] = risk_val if risk_val in _VALID_RISK_VALUES else "Low"
        ai_risk_val = str(raw_flags.get("ai_generated_risk") or "Low")
        base["flags"]["ai_generated_risk"] = ai_risk_val if ai_risk_val in _VALID_RISK_VALUES else "Low"
        base["flags"]["confidence_level"] = _clamp(_to_float(raw_flags.get("confidence_level"), 0.8), 0.0, 1.0)

    base["ai_generated"] = True
    base["question_type"] = "SQL"
    base["evaluation_version"] = "2.2.0"

    return base


# ─────────────────────────────────────────────────────────────
# Score enforcement
# ─────────────────────────────────────────────────────────────

def _enforce_score(result: dict, passed: bool, max_marks: float, deterministic_correctness: float) -> dict:
    """
    Compute final score from criteria scores.
    Correctness is already set deterministically — sum all criteria.
    Apply floor/cap as safety net.
    """
    if max_marks <= 0:
        max_marks = 1.0

    # Sum weighted criteria scores
    criteria = result.get("criteria_scores") or {}
    total_score = sum(
        float((criteria.get(k) or {}).get("score") or 0.0)
        for k in _CRITERIA_WEIGHTS
    )

    # Apply floor/cap
    if passed:
        total_score = max(total_score, max_marks * 0.80)
    else:
        total_score = min(total_score, max_marks * 0.50)

    total_score = max(0.0, min(total_score, max_marks))
    percentage = round((total_score / max_marks) * 100, 2)

    result["score"] = round(total_score, 4)
    result["percentage"] = percentage
    result["overall_score"] = round(percentage)
    result["criteria_scores"] = criteria
    return result


# ─────────────────────────────────────────────────────────────
# Fallback response
# ─────────────────────────────────────────────────────────────

def _fallback_response(req: dict, deterministic_correctness: float, comparison: dict) -> dict:
    """Deterministic fallback when Qwen fails — uses execution result as ground truth."""
    passed = bool((req.get("test_result") or {}).get("passed", False))
    max_marks = float(req.get("max_marks") or 1.0)
    if max_marks <= 0:
        max_marks = 1.0

    criteria: dict = {}
    for k, w in _CRITERIA_WEIGHTS.items():
        if k == "correctness":
            criteria[k] = {
                "score": deterministic_correctness,
                "weight": w,
                "feedback": "Based on execution result." if passed else "Query did not produce expected output.",
            }
        else:
            # Give partial credit for non-correctness criteria
            criteria[k] = {
                "score": round(max_marks * w * 0.5, 4),
                "weight": w,
                "feedback": "",
            }

    total_score = sum(c["score"] for c in criteria.values())
    if passed:
        total_score = max(total_score, max_marks * 0.80)
    else:
        total_score = min(total_score, max_marks * 0.50)
    total_score = max(0.0, min(total_score, max_marks))
    percentage = round((total_score / max_marks) * 100, 2)

    # Build feedback summary from comparison
    if passed:
        summary = f"Query executed successfully and returned {comparison.get('user_row_count', 0)} rows matching expected output."
    else:
        ratio = comparison.get("partial_match_ratio", 0.0)
        if ratio > 0.5:
            summary = f"Query returned {comparison.get('user_row_count', 0)} rows but did not fully match expected {comparison.get('expected_row_count', 0)} rows."
        else:
            summary = f"Query did not produce the expected output. Expected {comparison.get('expected_row_count', 0)} rows, got {comparison.get('user_row_count', 0)}."

    base = _empty_response_dict()
    base["question_id"] = req.get("question_id") or ""
    base["section"] = req.get("section") or ""
    base["max_marks"] = max_marks
    base["score"] = round(total_score, 4)
    base["percentage"] = percentage
    base["overall_score"] = round(percentage)
    base["criteria_scores"] = criteria
    base["feedback"]["summary"] = summary
    base["answer_log"]["submitted_answer"] = req.get("user_query") or ""
    base["answer_log"]["expected_answer"] = req.get("reference_query") or ""
    base["answer_log"]["partial_credit_reasoning"] = (
        f"Execution {'passed' if passed else 'failed'}. "
        f"Partial match ratio: {comparison.get('partial_match_ratio', 0.0):.1%}."
    )
    base["flags"]["requires_human_review"] = not passed
    return base


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_sql_feedback(*, payload: dict, usage_meta: dict | None) -> dict:
    """
    Main entry point called by the route handler.
    Accepts raw dict payload (validated by Pydantic at route level).
    Returns ai_feedback dict matching SQLAIFeedback schema.
    """
    question_id = str(payload.get("question_id") or "")
    user_query = str(payload.get("user_query") or "")
    max_marks = float(payload.get("max_marks") or 1.0)
    if max_marks <= 0:
        max_marks = 1.0
    use_cache = bool(payload.get("use_cache", True))
    tr = payload.get("test_result") or {}
    passed = bool(tr.get("passed", False))
    order_sensitive = bool(payload.get("order_sensitive", False))

    # ── 1. Parse and compare outputs ─────────────────────────────────
    user_rows = _parse_output(tr.get("user_output"))
    expected_rows = _parse_output(tr.get("expected_output"))
    comparison = _compare_outputs(user_rows, expected_rows, order_sensitive)

    # ── 2. Compute deterministic correctness (ground truth) ───────────
    deterministic_correctness = _compute_partial_credit(comparison, passed, max_marks)

    # ── 3. Short-circuit on empty / trivial query ─────────────────────
    if not user_query or len(user_query.strip()) < 10:
        logger.info("[SQL_EVAL] empty/trivial query for question_id=%s", question_id)
        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=0, cache_hit=False)
        return _empty_response(payload)

    # ── 4. Cache lookup ───────────────────────────────────────────────
    cache_key = hashlib.md5(
        f"{question_id}:{user_query}:{passed}:{order_sensitive}".encode()
    ).hexdigest()

    if use_cache and cache_key in _cache:
        logger.info("[SQL_EVAL] cache hit question_id=%s", question_id)
        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    # ── 5. Build messages ─────────────────────────────────────────────
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(payload, comparison, deterministic_correctness)},
    ]

    try:
        start = time.time()
        raw, prompt_tokens, completion_tokens = _llm_chat_coder(
            messages=messages, temperature=0.0, max_tokens=600
        )
        latency_ms = (time.time() - start) * 1000

        parsed = safe_parse(raw)

        if parsed.get("parse_error") is True:
            raise ValueError(f"safe_parse returned parse_error: {parsed.get('overall_summary', '')[:200]}")

        result = _normalize_product(parsed, max_marks, deterministic_correctness)
        result = _enforce_score(result, passed, max_marks, deterministic_correctness)

        # Populate metadata
        result["question_id"] = question_id
        result["section"] = payload.get("section") or ""
        result["max_marks"] = max_marks
        result["answer_log"]["submitted_answer"] = user_query
        result["answer_log"]["expected_answer"] = payload.get("reference_query") or ""
        result["answer_log"]["partial_credit_reasoning"] = (
            f"Execution {'passed' if passed else 'failed'}. "
            f"Rows: user={comparison['user_row_count']}, expected={comparison['expected_row_count']}. "
            f"Partial match: {comparison['partial_match_ratio']:.1%}."
        )

        emit_eval_usage(
            usage_meta, "sql_evaluation",
            latency_ms=latency_ms, cache_hit=False,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
        )

    except Exception as e:
        logger.warning("[SQL_EVAL] Qwen failed for question_id=%s: %s", question_id, str(e))
        emit_eval_usage(
            usage_meta, "sql_evaluation",
            latency_ms=0, status="error", error_detail=str(e),
        )
        result = _fallback_response(payload, deterministic_correctness, comparison)

    _cache[cache_key] = result
    return result
