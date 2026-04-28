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

_SYSTEM_PROMPT = """You are a strict SQL query evaluator. Return ONLY minified JSON — no markdown, no code fences, no extra keys, no whitespace outside strings.

Output schema (all keys required):
{"score":<float>,"criteria_scores":{"correctness":{"score":<float>,"weight":0.40,"feedback":"<string>"},"efficiency":{"score":<float>,"weight":0.25,"feedback":"<string>"},"best_practices":{"score":<float>,"weight":0.15,"feedback":"<string>"},"edge_cases":{"score":<float>,"weight":0.10,"feedback":"<string>"},"alternative_solutions":{"score":<float>,"weight":0.10,"feedback":"<string>"}},"feedback":{"summary":"<2 sentences>","strengths":["<string>"],"weaknesses":["<string>"],"detailed_analysis":"<string>","suggestions":["<string>"]},"answer_log":{"key_points_covered":["<string>"],"key_points_missed":["<string>"],"partial_credit_reasoning":"<string>"},"areas_of_improvement":[{"skill":"<string>","current_level":"<string>","gap_analysis":"<string>","priority":"<High|Medium|Low>","improvement_suggestions":[{"suggestion":"<string>","resources":[],"practice_exercises":[],"estimated_time":"<string>"}]}],"benchmarking":{"compared_to_peers":"<string>","percentile":<float 0-100>,"industry_standard":"<string>"},"insights":{"approach_quality":"<string>","edge_case_handling":"<string>","alternative_solutions":["<string>"]},"flags":{"plagiarism_risk":"<Low|Medium|High>","ai_generated_risk":"<Low|Medium|High>","confidence_level":<float 0-1>}}

Evaluation criteria:
- correctness (40%): result set matches expected output (considering order_sensitive flag)
- efficiency (25%): index usage, full table scans, window functions vs correlated subqueries, join strategy
- best_practices (15%): aliases, formatting, readability, SQL conventions, avoiding SELECT *
- edge_cases (10%): NULL handling, empty result sets, boundary conditions, type coercion
- alternative_solutions (10%): better approaches using CTEs, window functions, set operations

EFFICIENCY LANGUAGE — SQL-specific terms ONLY. FORBIDDEN: O(n), O(n²), O(log n), Big-O notation.
USE INSTEAD: "full table scan", "index seek", "index scan", "correlated subquery overhead", "hash join", "nested loop join", "covering index", "N+1 query pattern".

Score floor/cap (enforced by post-processing — apply as a hint):
- If passed=true: score should be at least 80% of max_marks
- If passed=false: score should be at most 50% of max_marks

Be concise and specific. No praise fluff. Output must end with '}' and contain nothing after it."""


# ─────────────────────────────────────────────────────────────
# User prompt construction
# ─────────────────────────────────────────────────────────────

def _build_user_prompt(req: dict) -> str:
    desc = (req.get("question_description") or "")[:1000]
    user_q = req.get("user_query") or ""
    ref_q = req.get("reference_query") or ""
    schemas_str = json.dumps(req.get("schemas") or {}, indent=2)[:800]
    tr = req.get("test_result") or {}
    user_out = (tr.get("user_output") or "")[:500]
    exp_out = (tr.get("expected_output") or "")[:500]
    error = (tr.get("error") or "")[:300]
    passed = bool(tr.get("passed", False))

    return (
        f"question_description: {desc}\n"
        f"difficulty: {req.get('difficulty', 'medium')}\n"
        f"order_sensitive: {req.get('order_sensitive', False)}\n"
        f"max_marks: {req.get('max_marks', 100)}\n\n"
        f"schemas:\n{schemas_str}\n\n"
        f"candidate_query:\n{user_q}\n\n"
        f"reference_query (for context only — do not expose to candidate):\n{ref_q}\n\n"
        f"test_result:\n"
        f"  passed: {passed}\n"
        f"  user_output: {user_out}\n"
        f"  expected_output: {exp_out}\n"
        f"  error: {error or 'None'}\n\n"
        f"Return ONLY the minified JSON described in the system prompt."
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

    # Handle parse_error from safe_parse
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

    # feedback
    raw_fb = raw.get("feedback") or {}
    if isinstance(raw_fb, dict):
        base["feedback"]["summary"] = _to_str(raw_fb.get("summary"))
        base["feedback"]["strengths"] = _to_list_of_str(raw_fb.get("strengths"))
        base["feedback"]["weaknesses"] = _to_list_of_str(raw_fb.get("weaknesses"))
        base["feedback"]["detailed_analysis"] = _to_str(raw_fb.get("detailed_analysis"))
        base["feedback"]["suggestions"] = _to_list_of_str(raw_fb.get("suggestions"))

    # answer_log — expected_answer always ""
    raw_al = raw.get("answer_log") or {}
    if isinstance(raw_al, dict):
        base["answer_log"]["key_points_covered"] = _to_list_of_str(raw_al.get("key_points_covered"))
        base["answer_log"]["key_points_missed"] = _to_list_of_str(raw_al.get("key_points_missed"))
        base["answer_log"]["partial_credit_reasoning"] = _to_str(raw_al.get("partial_credit_reasoning"))
    base["answer_log"]["expected_answer"] = ""  # never expose reference query

    # areas_of_improvement
    raw_aoi = raw.get("areas_of_improvement") or []
    if isinstance(raw_aoi, list):
        norm_aoi = []
        for item in raw_aoi:
            if not isinstance(item, dict):
                continue
            raw_suggestions = item.get("improvement_suggestions") or []
            norm_suggestions = []
            if isinstance(raw_suggestions, list):
                for s in raw_suggestions:
                    if isinstance(s, dict):
                        norm_suggestions.append({
                            "suggestion": _to_str(s.get("suggestion")),
                            "resources": _to_list_of_str(s.get("resources")),
                            "practice_exercises": _to_list_of_str(s.get("practice_exercises")),
                            "estimated_time": _to_str(s.get("estimated_time")),
                        })
            norm_aoi.append({
                "skill": _to_str(item.get("skill")),
                "current_level": _to_str(item.get("current_level")),
                "gap_analysis": _to_str(item.get("gap_analysis")),
                "priority": _to_str(item.get("priority")),
                "improvement_suggestions": norm_suggestions,
            })
        base["areas_of_improvement"] = norm_aoi

    # benchmarking
    raw_bm = raw.get("benchmarking") or {}
    if isinstance(raw_bm, dict):
        base["benchmarking"]["compared_to_peers"] = _to_str(raw_bm.get("compared_to_peers"))
        base["benchmarking"]["percentile"] = _clamp(_to_float(raw_bm.get("percentile"), 0.0), 0.0, 100.0)
        base["benchmarking"]["industry_standard"] = _to_str(raw_bm.get("industry_standard"))

    # insights
    raw_ins = raw.get("insights") or {}
    if isinstance(raw_ins, dict):
        base["insights"]["approach_quality"] = _to_str(raw_ins.get("approach_quality"))
        base["insights"]["edge_case_handling"] = _to_str(raw_ins.get("edge_case_handling"))
        base["insights"]["alternative_solutions"] = _to_list_of_str(raw_ins.get("alternative_solutions"))

    # flags
    raw_flags = raw.get("flags") or {}
    if isinstance(raw_flags, dict):
        risk_val = str(raw_flags.get("plagiarism_risk") or "Low")
        base["flags"]["plagiarism_risk"] = risk_val if risk_val in _VALID_RISK_VALUES else "Low"
        ai_risk_val = str(raw_flags.get("ai_generated_risk") or "Low")
        base["flags"]["ai_generated_risk"] = ai_risk_val if ai_risk_val in _VALID_RISK_VALUES else "Low"
        base["flags"]["confidence_level"] = _clamp(_to_float(raw_flags.get("confidence_level"), 0.0), 0.0, 1.0)

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
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=700)
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

        emit_eval_usage(usage_meta, "sql_evaluation", latency_ms=latency_ms, cache_hit=False)

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
