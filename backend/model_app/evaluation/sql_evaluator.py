"""SQL AI Evaluator — follows the exact DSA/AIML evaluator pattern.

Flow:
  1. Check cache (TTLCache, keyed on question_id + user_query + passed)
  2. Short-circuit on empty/trivial queries
  3. Call Qwen coder model with SQL-specific prompt
  4. Normalize response to contract schema
  5. Enforce score floor/cap as hard post-processing
  6. Store in cache, emit billing usage
  7. Fallback to deterministic score on any failure
"""
from __future__ import annotations

import hashlib
import json
import logging
import time

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache: TTLCache = TTLCache(maxsize=500, ttl=3600)

_CRITERIA_WEIGHTS: dict[str, float] = {
    "correctness": 0.40,
    "efficiency": 0.25,
    "best_practices": 0.15,
    "edge_cases": 0.10,
    "alternative_solutions": 0.10,
}

_VALID_RISK_VALUES = {"Low", "Medium", "High"}

_SYSTEM_PROMPT = """You are a strict SQL query evaluator. Return ONLY minified JSON — no markdown, no code fences, no extra text.

Output schema (all keys required):
{"score":<float 0-max_marks>,"criteria_scores":{"correctness":{"score":<float>,"weight":0.40,"feedback":"<1 sentence>"},"efficiency":{"score":<float>,"weight":0.25,"feedback":"<1 sentence>"},"best_practices":{"score":<float>,"weight":0.15,"feedback":"<1 sentence>"},"edge_cases":{"score":<float>,"weight":0.10,"feedback":"<1 sentence>"},"alternative_solutions":{"score":<float>,"weight":0.10,"feedback":"<1 sentence>"}},"feedback":{"summary":"<2 sentences>","strengths":["<string>"],"weaknesses":["<string>"],"suggestions":["<string>"]},"flags":{"plagiarism_risk":"Low","ai_generated_risk":"Low","confidence_level":<float 0-1>}}

Evaluation criteria:
- correctness (40%): result set matches expected output
- efficiency (25%): use SQL-specific terms only — "full table scan", "index seek", "hash join", "N+1 query"
- best_practices (15%): aliases, formatting, avoiding SELECT *
- edge_cases (10%): NULL handling, empty results, boundary conditions
- alternative_solutions (10%): CTEs, window functions, set operations

Score floor/cap:
- passed=true: score >= 80% of max_marks
- passed=false: score <= 50% of max_marks

Rules:
- Max 2 items per list.
- Keep each string under 100 characters.
- Output must end with } and contain nothing after it."""


# ─────────────────────────────────────────────────────────────
# User prompt construction
# ─────────────────────────────────────────────────────────────

def _build_user_prompt(req: dict) -> str:
    desc = (req.get("question_description") or "")[:300]
    user_q = req.get("user_query") or ""
    ref_q = req.get("reference_query") or ""
    schemas_str = json.dumps(req.get("schemas") or {})[:300]
    tr = req.get("test_result") or {}
    user_out = (tr.get("user_output") or "")[:200]
    exp_out = (tr.get("expected_output") or "")[:200]
    error = (tr.get("error") or "")[:150]
    passed = bool(tr.get("passed", False))

    return (
        f"question: {desc}\n"
        f"difficulty: {req.get('difficulty', 'medium')}\n"
        f"max_marks: {req.get('max_marks', 100)}\n"
        f"order_sensitive: {req.get('order_sensitive', False)}\n\n"
        f"schemas: {schemas_str}\n\n"
        f"candidate_query: {user_q}\n\n"
        f"reference_query (context only): {ref_q}\n\n"
        f"test_result:\n"
        f"  passed: {passed}\n"
        f"  user_output: {user_out}\n"
        f"  expected_output: {exp_out}\n"
        f"  error: {error or 'None'}\n\n"
        f"Return ONLY the JSON described in the system prompt."
    )


# ─────────────────────────────────────────────────────────────
# Empty / default response builders
# ─────────────────────────────────────────────────────────────

def _empty_response_dict() -> dict:
    """Fully-keyed dict with safe defaults matching the full contract."""
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
        "evaluation_version": "2.1.0",
        "ai_generated": True,
    }


def _empty_response(req: dict) -> dict:
    """Zero-score response for empty/trivial queries."""
    base = _empty_response_dict()
    base["question_id"] = req.get("question_id") or ""
    base["section"] = req.get("section") or ""
    base["max_marks"] = float(req.get("max_marks") or 0)
    base["answer_log"]["submitted_answer"] = req.get("user_query") or ""
    base["answer_log"]["expected_answer"] = ""
    base["flags"]["incomplete_answer"] = True
    return base


# ─────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────

def _normalize_product(raw: dict, max_marks: float) -> dict:
    """Normalize Qwen output to the full contract schema with safe defaults."""
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
    # overall_score will be set after _enforce_score computes percentage

    # criteria_scores
    raw_criteria = raw.get("criteria_scores") or {}
    if isinstance(raw_criteria, dict):
        for k, w in _CRITERIA_WEIGHTS.items():
            raw_c = raw_criteria.get(k) or {}
            if isinstance(raw_c, dict):
                c_score = _clamp(_to_float(raw_c.get("score"), 0.0), 0.0, max_marks * w)
                base["criteria_scores"][k] = {
                    "score": c_score,
                    "weight": w,
                    "feedback": _to_str(raw_c.get("feedback")),
                }

    # feedback — simplified schema, populate what we have
    raw_fb = raw.get("feedback") or {}
    if isinstance(raw_fb, dict):
        base["feedback"]["summary"] = _to_str(raw_fb.get("summary"))
        base["feedback"]["strengths"] = _to_list_of_str(raw_fb.get("strengths"))
        base["feedback"]["weaknesses"] = _to_list_of_str(raw_fb.get("weaknesses"))
        base["feedback"]["suggestions"] = _to_list_of_str(raw_fb.get("suggestions"))
        # detailed_analysis not in simplified schema — leave as empty string

    # flags — simplified schema
    raw_flags = raw.get("flags") or {}
    if isinstance(raw_flags, dict):
        risk_val = str(raw_flags.get("plagiarism_risk") or "Low")
        base["flags"]["plagiarism_risk"] = risk_val if risk_val in _VALID_RISK_VALUES else "Low"
        ai_risk_val = str(raw_flags.get("ai_generated_risk") or "Low")
        base["flags"]["ai_generated_risk"] = ai_risk_val if ai_risk_val in _VALID_RISK_VALUES else "Low"
        base["flags"]["confidence_level"] = _clamp(_to_float(raw_flags.get("confidence_level"), 0.8), 0.0, 1.0)

    # Force invariants
    base["ai_generated"] = True
    base["question_type"] = "SQL"
    base["evaluation_version"] = "2.1.0"

    return base


# ─────────────────────────────────────────────────────────────
# Score enforcement
# ─────────────────────────────────────────────────────────────

def _enforce_score(result: dict, passed: bool, max_marks: float) -> dict:
    """Apply floor/cap and redistribute criteria scores proportionally."""
    if max_marks <= 0:
        max_marks = 1.0

    raw_score = float(result.get("score") or 0.0)

    # Apply floor / cap
    if passed:
        score = max(raw_score, max_marks * 0.8)
    else:
        score = min(raw_score, max_marks * 0.5)

    # Clamp to [0, max_marks]
    score = max(0.0, min(score, max_marks))

    # Recompute percentage
    percentage = round((score / max_marks) * 100, 2)

    # Redistribute criteria_scores proportionally
    criteria = result.get("criteria_scores") or {}
    weighted_sum = sum(
        float((criteria.get(k) or {}).get("score") or 0.0) * w
        for k, w in _CRITERIA_WEIGHTS.items()
    )

    if weighted_sum > 0 and abs(weighted_sum - score) > 0.01:
        scale = score / weighted_sum
        for k, w in _CRITERIA_WEIGHTS.items():
            if k in criteria and isinstance(criteria[k], dict):
                old = float(criteria[k].get("score") or 0.0)
                max_criterion = max_marks * w
                criteria[k]["score"] = round(max(0.0, min(old * scale, max_criterion)), 4)
    elif weighted_sum == 0 and score > 0:
        # Distribute proportionally by weight when all criteria are 0
        for k, w in _CRITERIA_WEIGHTS.items():
            if k not in criteria or not isinstance(criteria.get(k), dict):
                criteria[k] = {"score": 0.0, "weight": w, "feedback": ""}
            criteria[k]["score"] = round(score * w, 4)

    result["score"] = round(score, 4)
    result["percentage"] = percentage
    result["criteria_scores"] = criteria
    result["overall_score"] = round(percentage)
    return result


# ─────────────────────────────────────────────────────────────
# Fallback response
# ─────────────────────────────────────────────────────────────

def _fallback_response(req: dict) -> dict:
    """Deterministic fallback when Qwen fails."""
    passed = bool((req.get("test_result") or {}).get("passed", False))
    max_marks = float(req.get("max_marks") or 1.0)
    if max_marks <= 0:
        max_marks = 1.0

    score = max_marks * 0.8 if passed else max_marks * 0.3
    percentage = round((score / max_marks) * 100, 2)

    criteria: dict = {}
    for k, w in _CRITERIA_WEIGHTS.items():
        criteria[k] = {
            "score": round(score * w, 4),
            "weight": w,
            "feedback": "",
        }

    base = _empty_response_dict()
    base["question_id"] = req.get("question_id") or ""
    base["section"] = req.get("section") or ""
    base["max_marks"] = max_marks
    base["score"] = round(score, 4)
    base["percentage"] = percentage
    base["overall_score"] = round(percentage)
    base["criteria_scores"] = criteria
    base["feedback"]["summary"] = "Automated scoring applied. Human review recommended."
    base["answer_log"]["submitted_answer"] = req.get("user_query") or ""
    base["answer_log"]["expected_answer"] = ""
    base["flags"]["requires_human_review"] = True
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

    # Short-circuit on empty / trivial query
    if not user_query or len(user_query.strip()) < 10:
        logger.info("[SQL_EVAL] empty/trivial query for question_id=%s", question_id)
        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=0, cache_hit=False)
        return _empty_response(payload)

    # Cache lookup
    cache_key = hashlib.md5(
        f"{question_id}:{user_query}:{passed}".encode()
    ).hexdigest()

    if use_cache and cache_key in _cache:
        logger.info("[SQL_EVAL] cache hit question_id=%s", question_id)
        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    # Build messages
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(payload)},
    ]

    try:
        start = time.time()
        raw, prompt_tokens, completion_tokens = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=500)
        latency_ms = (time.time() - start) * 1000

        parsed = safe_parse(raw)

        # Treat parse_error as failure → fallback
        if parsed.get("parse_error") is True:
            raise ValueError(f"safe_parse returned parse_error: {parsed.get('overall_summary', '')[:200]}")

        result = _normalize_product(parsed, max_marks)
        result = _enforce_score(result, passed, max_marks)

        # Populate metadata fields
        result["question_id"] = question_id
        result["section"] = payload.get("section") or ""
        result["max_marks"] = max_marks
        result["answer_log"]["submitted_answer"] = user_query
        result["answer_log"]["expected_answer"] = ""

        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=latency_ms, cache_hit=False,
                        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

    except Exception as e:
        logger.warning("[SQL_EVAL] Qwen failed for question_id=%s: %s", question_id, str(e))
        emit_eval_usage(
            usage_meta,
            "sql_evaluation",
            latency_ms=0,
            status="error",
            error_detail=str(e),
        )
        result = _fallback_response(payload)

    _cache[cache_key] = result
    return result
