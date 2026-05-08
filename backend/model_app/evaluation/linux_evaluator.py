"""Linux / Shell Command Evaluator.

Evaluates candidate terminal sessions for Linux/Shell competency questions.
Follows the same pattern as devops_evaluator.py but with Linux-specific
system prompts that understand shell concepts: pipes, redirects, file
permissions, process management, text processing, etc.

Response contract is identical to the DevOps ai_feedback shape.
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

def _clear_none_from_cache():
    """Remove any None values from cache (from previous failed runs)"""
    keys_to_delete = [k for k, v in list(_cache.items()) if v is None]
    for k in keys_to_delete:
        try:
            del _cache[k]
        except Exception:
            pass

# Clear stale None entries on module load
_clear_none_from_cache()

# ─────────────────────────────────────────────────────────────
# System prompts — Linux/Shell specific
# ─────────────────────────────────────────────────────────────

_TERMINAL_SYSTEM_PROMPT = """You are an automated Linux/Shell evaluator. Return ONLY raw JSON, no markdown, no fences.

Identify ALL tasks from the question description (up to 10 tasks). Each task = 100/total_tasks marks.
Evaluate each task from terminal_history: completed=true only if command ran AND produced correct result.
IMPORTANT: If a task is NOT present in terminal_history, mark it completed=false and score=0.

JSON format (MUST be complete and valid):
{"derived_tasks":[{"task":"<task>","completed":true,"score":<marks>,"max_score":<marks_per_task>,"evidence":"<cmd>","reasoning":"<short>"}],"overall_score":<0-100>,"feedback_summary":"<1 sentence>","one_liner":"<verdict>","ideal_answer_summary":"<brief>","code_quality":{"score":0,"comments":"<short>"},"correctness":{"score":0,"comments":"<short>"},"library_usage":{"score":0,"comments":"<short>"},"output_quality":{"score":0,"comments":"<short>"},"strengths":["<s1>"],"areas_for_improvement":["<a1>"],"improvement_suggestions":["<i1>"],"suggestions":["<s1>"],"deduction_reasons":["<d1>"]}

Rules: Up to 10 tasks. Max 2 list items. Keep all strings under 80 chars. No truncation."""

_SCENARIO_SYSTEM_PROMPT = """You are an automated Linux/Shell written-answer evaluator. Return ONLY raw JSON, no markdown, no fences.

Identify ALL tasks from the question description (up to 10 tasks). Each task = 100/total_tasks marks.
Evaluate each task from the written answer: completed=true only if correct command/explanation provided.
IMPORTANT: If a task is NOT addressed in the answer, mark it completed=false and score=0.

JSON format (MUST be complete and valid):
{"derived_tasks":[{"task":"<task>","completed":true,"score":<marks>,"max_score":<marks_per_task>,"evidence":"<quote>","reasoning":"<short>"}],"overall_score":<0-100>,"feedback_summary":"<1 sentence>","one_liner":"<verdict>","ideal_answer_summary":"<brief>","code_quality":{"score":0,"comments":"<short>"},"correctness":{"score":0,"comments":"<short>"},"library_usage":{"score":0,"comments":"<short>"},"output_quality":{"score":0,"comments":"<short>"},"strengths":["<s1>"],"areas_for_improvement":["<a1>"],"improvement_suggestions":["<i1>"],"suggestions":["<s1>"],"deduction_reasons":["<d1>"]}

Rules: Up to 10 tasks. Max 2 list items. Keep all strings under 80 chars. No truncation."""


# ─────────────────────────────────────────────────────────────
# Helper functions (same as devops_evaluator)
# ─────────────────────────────────────────────────────────────

def _cache_key(question_id: str, submission: dict) -> str:
    payload = f"{question_id}:{json.dumps(submission, sort_keys=True, default=str)}"
    return hashlib.md5(payload.encode()).hexdigest()


def _empty_response() -> dict:
    return {
        "overall_score": 0,
        "feedback_summary": "",
        "one_liner": "",
        "code_quality":    {"score": 0, "comments": ""},
        "correctness":     {"score": 0, "comments": ""},
        "library_usage":   {"score": 0, "comments": ""},
        "output_quality":  {"score": 0, "comments": ""},
        "task_completion": {
            "score": 0,
            "comments": "",
            "completed": 0,
            "total": 0,
            "details": [],
        },
        "strengths":               [],
        "areas_for_improvement":   [],
        "suggestions":             [],
        "improvement_suggestions": [],
        "deduction_reasons":       [],
        "derived_tasks":           [],
        "ideal_answer_summary":    "",
        "ai_generated":            True,
    }


def _compute_scores(derived_tasks: list[dict]) -> tuple[int, int, int]:
    """
    Compute overall_score from derived_tasks.
    Uses LLM-provided scores if available, otherwise computes from completed flag.
    Returns (overall_score, completed_count, total_count).
    """
    total = len(derived_tasks)
    if total == 0:
        return 0, 0, 0
    completed = sum(1 for t in derived_tasks if t.get("completed", False))
    # Use LLM-provided overall score if tasks have scores
    total_score = sum(float(t.get("score", 0)) for t in derived_tasks)
    overall_score = round(min(100, total_score))
    return overall_score, completed, total


def _detect_mode(submission: dict) -> str:
    history = submission.get("terminal_history") or []
    er = submission.get("engine_response") or {}
    if (isinstance(history, list) and len(history) > 0) or er.get("exit_code") is not None:
        return "terminal"
    return "scenario"


# ─────────────────────────────────────────────────────────────
# Prompt builders — Linux-aware field extraction
# ─────────────────────────────────────────────────────────────

def _build_terminal_user_prompt(question: dict, submission: dict) -> str:
    q = question
    s = submission
    vs = (s.get("validation_signals") or {})
    er = (s.get("engine_response") or {})

    # Cap history to last 10 entries, commands to 100 chars, output to 100 chars
    history = s.get("terminal_history") or []
    history_lines = []
    for entry in history[-10:]:
        cmd = str(entry.get("command") or "")[:100]
        out = str(entry.get("output") or "")[:100]
        history_lines.append(f"$ {cmd}\n{out}" if out.strip() else f"$ {cmd}")
    history_block = "\n".join(history_lines) or "(empty)"

    return (
        f"QUESTION:\n"
        f"title: {q.get('title', '')[:100]}\n"
        f"description: {str(q.get('description', ''))[:500]}\n\n"
        f"STUDENT ANSWER:\n{history_block}\n\n"
        f"passed: {vs.get('passed', False)} | exit_code: {er.get('exit_code')}\n\n"
        f"Return ONLY the JSON."
    )


def _build_scenario_user_prompt(question: dict, submission: dict) -> str:
    q = question
    s = submission
    answer = str(s.get("answer") or "")[:600]

    return (
        f"QUESTION:\n"
        f"title: {q.get('title', '')[:100]}\n"
        f"description: {str(q.get('description', ''))[:500]}\n\n"
        f"STUDENT ANSWER:\n{answer}\n\n"
        f"Return ONLY the JSON."
    )


# ─────────────────────────────────────────────────────────────
# Response normalization
# ─────────────────────────────────────────────────────────────

def _normalize_response(raw: dict, validation_signals: dict | None = None) -> dict:
    base = _empty_response()
    if not isinstance(raw, dict) or raw.get("parse_error"):
        return base

    def _str(v, max_len: int = 500) -> str:
        return str(v)[:max_len] if v is not None else ""

    def _list_of_str(v, max_items: int = 3) -> list[str]:
        if not isinstance(v, list):
            return []
        return [str(x) for x in v[:max_items] if str(x).strip()]

    def _int_clamp(v, lo: int = 0, hi: int = 100) -> int:
        try:
            return max(lo, min(hi, int(v)))
        except Exception:
            return lo

    # Derived tasks — source of truth for scoring
    raw_tasks = raw.get("derived_tasks") or []
    derived_tasks: list[dict] = []
    total_tasks = len([t for t in raw_tasks if isinstance(t, dict)])
    per_task_score = round(100 / total_tasks, 2) if total_tasks > 0 else 0

    if isinstance(raw_tasks, list):
        for t in raw_tasks:
            if not isinstance(t, dict):
                continue
            llm_score = t.get("score")
            llm_max = t.get("max_score", per_task_score)
            completed = bool(t.get("completed", False))
            if llm_score is not None:
                try:
                    task_score = float(llm_score)
                except Exception:
                    task_score = per_task_score if completed else 0
            else:
                task_score = per_task_score if completed else 0

            derived_tasks.append({
                "task":      _str(t.get("task"), 200),
                "score":     round(task_score, 2),
                "max_score": round(float(llm_max) if llm_max else per_task_score, 2),
                "completed": completed,
                "evidence":  _str(t.get("evidence"), 300),
                "reasoning": _str(t.get("reasoning"), 200),
            })

    # Compute overall_score from task scores (don't trust LLM's overall_score)
    overall_score, completed_count, total_count = _compute_scores(derived_tasks)
    base["derived_tasks"] = derived_tasks
    base["overall_score"] = overall_score

    base["task_completion"] = {
        "score":     overall_score,
        "comments":  _str(raw.get("feedback_summary"), 300),
        "completed": completed_count,
        "total":     total_count,
        "details":   [t["task"] for t in derived_tasks if t["completed"]],
    }

    base["feedback_summary"]     = _str(raw.get("feedback_summary"), 500)
    base["one_liner"]            = _str(raw.get("one_liner"), 200)
    base["ideal_answer_summary"] = _str(raw.get("ideal_answer_summary"), 500)

    base["strengths"]               = _list_of_str(raw.get("strengths"))
    base["areas_for_improvement"]   = _list_of_str(raw.get("areas_for_improvement"))
    base["suggestions"]             = _list_of_str(raw.get("suggestions"))
    base["improvement_suggestions"] = _list_of_str(raw.get("improvement_suggestions") or raw.get("suggestions"))
    base["deduction_reasons"]       = _list_of_str(raw.get("deduction_reasons"))

    # Scored sub-objects
    for key in ("code_quality", "correctness", "library_usage", "output_quality"):
        raw_sub = raw.get(key)
        if isinstance(raw_sub, dict):
            base[key] = {
                "score":    _int_clamp(raw_sub.get("score", 0)),
                "comments": _str(raw_sub.get("comments", ""), 300),
            }

    base["ai_generated"] = True
    return base


def _fallback_response(validation_signals: dict | None = None) -> dict:
    vs = validation_signals or {}
    score = 0
    try:
        qs = vs.get("question_score")
        if qs is not None:
            score = int(qs)
    except Exception:
        pass

    base = _empty_response()
    base["overall_score"]    = score
    base["feedback_summary"] = "Automated scoring applied. Human review recommended."
    base["one_liner"]        = "Evaluation unavailable."
    base["task_completion"]["score"] = score
    base["ai_generated"] = True
    return base


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_linux_feedback(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Main entry point for Linux/Shell evaluation.
    Accepts raw dict payload (validated by Pydantic at route level).
    Returns ai_feedback dict matching the Aaptor contract.
    """
    question = payload.get("question") or {}
    submission = payload.get("submission") or {}
    use_cache = bool(payload.get("use_cache", True))
    question_id = str(question.get("id") or "")
    vs = (submission.get("validation_signals") or {})

    # Short-circuit on empty submission
    answer = str(submission.get("answer") or "").strip()
    history = submission.get("terminal_history") or []
    if not answer and not (isinstance(history, list) and len(history) > 0):
        logger.info("[LINUX_EVAL] empty submission for question_id=%s", question_id)
        emit_eval_usage(usage_meta, "linux_evaluation", latency_ms=0, cache_hit=False)
        return _empty_response()

    # Cache lookup
    cache_key = _cache_key(question_id, submission)
    if use_cache and cache_key in _cache:
        cached = _cache[cache_key]
        if cached is not None:
            logger.info("[LINUX_EVAL] cache hit question_id=%s", question_id)
            emit_eval_usage(usage_meta, "linux_evaluation", latency_ms=0, cache_hit=True)
            return cached
        else:
            # Remove stale None from cache
            del _cache[cache_key]

    # Detect mode and build prompt
    mode = _detect_mode(submission)
    if mode == "terminal":
        system_prompt = _TERMINAL_SYSTEM_PROMPT
        user_prompt = _build_terminal_user_prompt(question, submission)
    else:
        system_prompt = _SCENARIO_SYSTEM_PROMPT
        user_prompt = _build_scenario_user_prompt(question, submission)

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user",   "content": user_prompt},
    ]

    try:
        start = time.time()
        raw, prompt_tokens, completion_tokens = _llm_chat_coder(messages=messages, temperature=0.1, max_tokens=900)
        latency_ms = (time.time() - start) * 1000

        parsed = safe_parse(raw)
        if parsed.get("parse_error") is True:
            raise ValueError(f"safe_parse returned parse_error: {parsed.get('overall_summary', '')[:200]}")

        result = _normalize_response(parsed, vs)
        emit_eval_usage(
            usage_meta,
            "linux_evaluation",
            latency_ms=latency_ms,
            cache_hit=False,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    except Exception as e:
        logger.warning("[LINUX_EVAL] Qwen failed for question_id=%s: %s", question_id, str(e))
        emit_eval_usage(
            usage_meta,
            "linux_evaluation",
            latency_ms=0,
            status="error",
            error_detail=str(e),
        )
        result = _fallback_response(vs)

    if result is not None:
        _cache[cache_key] = result
    return result
