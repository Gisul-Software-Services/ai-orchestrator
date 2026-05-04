"""AIML / ML Code Evaluator — Production-ready redesign.

Evaluates ML/AI code submissions (Python-first) against task requirements,
test results, and execution outputs.

Scoring formula:
  overall_score = round((task_score × 0.50) + (code_quality × 0.25) + (output_quality × 0.25))
  where task_score = round((completed_tasks / total_tasks) × 100)

Response contract matches Aaptor's EvaluateSubmissionResponse shape.
"""
from __future__ import annotations

import hashlib
import json
import logging
import time

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=500, ttl=3600)

# ─────────────────────────────────────────────────────────────
# System prompt — compact, clear schema, 0-100 scores
# ─────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """You are a strict ML/AI code evaluator. Score on a 0-100 scale.

Scoring formula:
  overall_score = round((task_score × 0.50) + (code_quality.score × 0.25) + (output_quality.score × 0.25))
  where task_score = round((completed_tasks / total_tasks) × 100)

Return ONLY minified JSON — no markdown, no code fences, no explanation:
{"overall_score":0,"feedback_summary":"<4-5 sentences covering: 1) overall performance, 2) what was done correctly, 3) what was missing or wrong, 4) code quality observations, 5) one specific actionable improvement>","one_liner":"<single sentence verdict>","task_scores":[{"task_number":1,"task_description":"<task>","score":0,"max_score":10,"status":"completed|partially_completed|not_attempted","feedback":""}],"task_completion":{"completed":0,"total":0,"details":["<completed task name>"]},"code_quality":{"score":0,"comments":"<specific comment on ML code quality, library usage, best practices>"},"library_usage":{"score":0,"comments":"<comment on correct use of sklearn/pandas/numpy/etc>"},"output_quality":{"score":0,"comments":"<comment on model performance, metrics, output correctness>"},"strengths":["<strength>"],"areas_for_improvement":["<area>"],"suggestions":["<suggestion>"],"deduction_reasons":["<reason>"]}

Rules:
- overall_score MUST be 0-100. Apply the formula above.
- task_score = round((completed_tasks / total_tasks) × 100) where completed = tasks with status "completed".
- code_quality.score, library_usage.score, output_quality.score are all 0-100.
- feedback_summary MUST be 4-5 sentences. Cover: overall result, correct parts, gaps, code quality, one improvement.
- Max 4 items per list field.
- Keep each string under 200 characters.
- If code is empty or < 20 chars, set all scores to 0.
- Do NOT reveal hidden test case details. Refer to failures by count only."""


# ─────────────────────────────────────────────────────────────
# Prompt builder
# ─────────────────────────────────────────────────────────────

def _build_user_prompt(payload: dict) -> str:
    code = str(payload.get("source_code") or "")[:800]
    title = str(payload.get("question_title") or "")
    desc = str(payload.get("question_description") or "")[:300]
    difficulty = str(payload.get("difficulty") or "")
    tasks = payload.get("tasks") or []
    constraints = payload.get("constraints") or []
    outputs = payload.get("outputs") or []
    test_cases = payload.get("test_cases") or []

    task_lines = "\n".join(
        f"  {i+1}. {str(t)[:120]}" for i, t in enumerate(tasks[:6])
    ) or "  None"

    constraint_lines = "\n".join(
        f"  - {str(c)[:100]}" for c in constraints[:3]
    ) or "  None"

    # Test case summary — counts only, no hidden details
    total_tc = len(test_cases) if isinstance(test_cases, list) else 0
    passed_tc = sum(
        1 for tc in (test_cases or [])
        if isinstance(tc, dict) and str(tc.get("status", "")).lower() in ("passed", "completed", "success")
    )

    # Output summary — cap each output
    out_lines = []
    if isinstance(outputs, list):
        for o in outputs[:3]:
            out_lines.append(f"  {str(o)[:200]}")
    out_block = "\n".join(out_lines) or "  None"

    return (
        f"question: {title}\n"
        f"description: {desc}\n"
        f"difficulty: {difficulty}\n\n"
        f"tasks:\n{task_lines}\n\n"
        f"constraints:\n{constraint_lines}\n\n"
        f"test_results: {passed_tc}/{total_tc} passed\n\n"
        f"execution_outputs:\n{out_block}\n\n"
        f"source_code:\n```python\n{code}\n```\n\n"
        f"Apply the scoring formula from the system prompt. Return ONLY JSON."
    )


# ─────────────────────────────────────────────────────────────
# Normalization
# ─────────────────────────────────────────────────────────────

def _normalize_product(raw: dict) -> dict:
    base = _product_empty()
    if not isinstance(raw, dict) or raw.get("parse_error"):
        if raw.get("parse_error"):
            summary = str(raw.get("overall_summary") or "")[:400]
            if summary:
                base["feedback_summary"] = summary
                base["one_liner"] = "Evaluation output was not valid JSON — please retry."
        return base

    def _int_clamp(v, lo=0, hi=100):
        try:
            return max(lo, min(hi, int(float(v))))
        except Exception:
            return lo

    def _str(v, max_len=300):
        return str(v)[:max_len] if v is not None else ""

    def _list_of_str(v, max_items=3):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v[:max_items] if str(x).strip()]

    def _norm_status(v) -> str:
        s = str(v or "").strip().lower().replace("-", "_").replace(" ", "_")
        if s in {"completed", "complete", "done", "success", "passed"}:
            return "completed"
        if s in {"partially_completed", "partial", "partially_complete", "incomplete"}:
            return "partially_completed"
        if s in {"attempted_incorrect", "incorrect", "wrong", "failed"}:
            return "attempted_incorrect"
        return "not_attempted"

    # Task scores
    raw_tasks = raw.get("task_scores") or []
    norm_tasks = []
    if isinstance(raw_tasks, list):
        for i, item in enumerate(raw_tasks):
            if not isinstance(item, dict):
                continue
            max_score = max(1, _int_clamp(item.get("max_score", 10), 0, 100))
            score = _int_clamp(item.get("score", 0), 0, max_score)
            status = _norm_status(item.get("status"))
            norm_tasks.append({
                "task_number":    _int_clamp(item.get("task_number", i + 1), 1, 100),
                "task_description": _str(item.get("task_description"), 200),
                "score":          score,
                "max_score":      max_score,
                "status":         status,
                "feedback":       _str(item.get("feedback"), 200),
            })
    base["task_scores"] = norm_tasks

    # Task completion — derive from task_scores for consistency
    completed = sum(1 for t in norm_tasks if t["status"] == "completed")
    partial = sum(1 for t in norm_tasks if t["status"] == "partially_completed")
    # Count partial as 0.5 for scoring purposes
    effective_completed = completed + (partial * 0.5)
    total_tasks_count = len(norm_tasks)

    base["task_completion"] = {
        "completed": completed,
        "total":     total_tasks_count,
        "details":   [t["task_description"] for t in norm_tasks if t["status"] in ("completed", "partially_completed")],
    }

    # Sub-scores
    cq_score = _int_clamp((raw.get("code_quality") or {}).get("score", 0))
    lu_score = _int_clamp((raw.get("library_usage") or {}).get("score", 0))
    oq_score = _int_clamp((raw.get("output_quality") or {}).get("score", 0))

    base["code_quality"]  = {"score": cq_score,  "comments": _str((raw.get("code_quality") or {}).get("comments", ""))}
    base["library_usage"] = {"score": lu_score,  "comments": _str((raw.get("library_usage") or {}).get("comments", ""))}
    base["output_quality"]= {"score": oq_score,  "comments": _str((raw.get("output_quality") or {}).get("comments", ""))}

    # Recompute overall_score using formula — derived from task_scores, not Qwen's value
    task_score = round((effective_completed / total_tasks_count) * 100) if total_tasks_count > 0 else 0
    overall = round((task_score * 0.50) + (cq_score * 0.25) + (oq_score * 0.25))
    overall = max(0, min(100, overall))
    base["overall_score"] = overall

    # Narrative fields
    base["feedback_summary"] = _str(raw.get("feedback_summary"), 500)
    base["one_liner"]        = _str(raw.get("one_liner"), 200)

    base["strengths"]             = _list_of_str(raw.get("strengths"))
    base["areas_for_improvement"] = _list_of_str(raw.get("areas_for_improvement"))
    base["suggestions"]           = _list_of_str(raw.get("suggestions"))
    base["deduction_reasons"]     = _list_of_str(raw.get("deduction_reasons"))

    base["ai_generated"] = True
    return base


def _product_empty() -> dict:
    return {
        "overall_score": 0,
        "feedback_summary": "",
        "one_liner": "",
        "task_scores": [],
        "task_completion": {"completed": 0, "total": 0, "details": []},
        "code_quality":   {"score": 0, "comments": ""},
        "library_usage":  {"score": 0, "comments": ""},
        "output_quality": {"score": 0, "comments": ""},
        "strengths":             [],
        "areas_for_improvement": [],
        "suggestions":           [],
        "deduction_reasons":     [],
        "ai_generated": True,
    }


def _fallback_response(payload: dict) -> dict:
    """Deterministic fallback when Qwen fails."""
    tasks = payload.get("tasks") or []
    base = _product_empty()
    base["feedback_summary"] = "Automated scoring applied. Human review recommended."
    base["one_liner"]        = "Evaluation unavailable."
    base["task_completion"]["total"] = len(tasks)
    return base


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_aiml_feedback_product_contract(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Redesigned AIML evaluator.
    - overall_score on 0-100 scale using formula
    - Compact prompt fits within 1024 token context
    - Score formula: task_score(50%) + code_quality(25%) + output_quality(25%)
    - Proper fallback with human review flag
    """
    code = str(payload.get("source_code") or "")
    title = str(payload.get("question_title") or "")
    outputs = payload.get("outputs") or []

    # Cache key
    cache_key = hashlib.md5(
        f"{title}:{code}:{json.dumps(outputs, sort_keys=True, default=str)[:500]}".encode()
    ).hexdigest()

    if cache_key in _cache:
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    # Short-circuit on empty code
    if not code or len(code.strip()) < 20:
        fb = _product_empty()
        _cache[cache_key] = fb
        return fb

    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user",   "content": _build_user_prompt(payload)},
    ]

    try:
        start = time.time()
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=900)
        latency_ms = (time.time() - start) * 1000
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=latency_ms, cache_hit=False)

        out = safe_parse(raw)
        if out.get("parse_error"):
            raise ValueError(f"safe_parse error: {out.get('overall_summary', '')[:200]}")

        fb = _normalize_product(out)

    except Exception as e:
        logger.warning("[AIML_EVAL] Qwen failed: %s", str(e))
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=0, status="error", error_detail=str(e))
        fb = _fallback_response(payload)

    _cache[cache_key] = fb
    return fb
