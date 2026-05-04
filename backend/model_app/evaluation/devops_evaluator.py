"""DevOps / Cloud AI Evaluator.

Replaces Aaptor's OpenAI-based evaluator with a Qwen-based equivalent.
Response contract is byte-for-byte compatible with Aaptor's ai_feedback shape.

Flow:
  1. Cache lookup (TTLCache, keyed on question_id + submission hash)
  2. Short-circuit on empty submission
  3. Auto-detect mode: terminal (has terminal_history / engine_response) or scenario (written answer)
  4. Build mode-specific Qwen prompt
  5. Call Qwen coder model
  6. Normalize response to ai_feedback contract
  7. Compute scores from derived_tasks (equal weight per task)
  8. Store in cache, emit billing usage
  9. Fallback to deterministic response on any failure
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

# ─────────────────────────────────────────────────────────────
# System prompts
# ─────────────────────────────────────────────────────────────

_TERMINAL_SYSTEM_PROMPT = """You are a strict DevOps/Cloud submission evaluator.

Analyse the candidate's terminal commands and outputs against the question requirements.
Derive exactly 3 to 7 concrete, verifiable tasks from the question.
For each task, decide completed: true or false based on execution evidence.
Use validation_signals.passed and validation_signals.reasons as supporting evidence only.

Return ONLY valid JSON — no markdown, no code fences, no explanation:
{"derived_tasks":[{"task":"<concise task>","completed":true,"evidence":"<what supports this>","reasoning":"<1 sentence>"}],"feedback_summary":"<2-3 sentences>","one_liner":"<single sentence verdict>","ideal_answer_summary":"<what a perfect submission looks like>","code_quality":{"score":0,"comments":"<comment on command structure and conventions>"},"correctness":{"score":0,"comments":"<comment on whether commands produce correct results>"},"library_usage":{"score":0,"comments":"<comment on correct use of CLI tools and flags>"},"output_quality":{"score":0,"comments":"<comment on output and verification steps>"},"strengths":["<strength>"],"areas_for_improvement":["<area>"],"suggestions":["<suggestion>"],"deduction_reasons":["<reason>"]}

Rules:
- Derive between 3 and 7 tasks. Never fewer, never more.
- Base task completion strictly on execution evidence in terminal_history and engine_response.
- If terminal_history is empty, mark all tasks incomplete and set all scores to 0.
- Do not invent evidence. If unsure, mark incomplete.
- Score each of code_quality, correctness, library_usage, output_quality from 0 to 100.
- Keep each string under 120 characters.
- Max 3 items per list field."""

_SCENARIO_SYSTEM_PROMPT = """You are a strict DevOps/Cloud written-answer evaluator.

Analyse the candidate's written answer against the question requirements.
Derive exactly 3 to 7 concrete, verifiable tasks from the question.
For each task, decide completed: true or false based on the written answer.
Use question instructions, hints, and constraints as the evaluation rubric.

Return ONLY valid JSON — no markdown, no code fences, no explanation:
{"derived_tasks":[{"task":"<concise task>","completed":true,"evidence":"<quote or paraphrase>","reasoning":"<1 sentence>"}],"feedback_summary":"<2-3 sentences>","one_liner":"<single sentence verdict>","ideal_answer_summary":"<what a perfect answer covers>","code_quality":{"score":0,"comments":"<comment on technical accuracy of any code or commands mentioned>"},"correctness":{"score":0,"comments":"<comment on correctness of the proposed solution>"},"library_usage":{"score":0,"comments":"<comment on correct use of tools, services, or APIs mentioned>"},"output_quality":{"score":0,"comments":"<comment on clarity and completeness of the explanation>"},"strengths":["<strength>"],"areas_for_improvement":["<area>"],"suggestions":["<suggestion>"],"deduction_reasons":["<reason>"]}

Rules:
- Derive between 3 and 7 tasks. Never fewer, never more.
- If the answer is empty or fewer than 20 characters, mark all tasks incomplete and set all scores to 0.
- Do not invent evidence. If unsure, mark incomplete.
- Score each of code_quality, correctness, library_usage, output_quality from 0 to 100.
- Keep each string under 120 characters.
- Max 3 items per list field."""


# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────

def _cache_key(question_id: str, submission: dict) -> str:
    payload = f"{question_id}:{json.dumps(submission, sort_keys=True, default=str)}"
    return hashlib.md5(payload.encode()).hexdigest()


def _empty_response() -> dict:
    """Full ai_feedback dict with all required keys and safe defaults."""
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
    Compute overall_score and per-task scores from derived_tasks.
    Returns (overall_score, completed_count, total_count).
    Mutates each task dict to set task["score"].
    """
    total = len(derived_tasks)
    if total == 0:
        return 0, 0, 0
    completed = sum(1 for t in derived_tasks if t.get("completed", False))
    overall_score = round((completed / total) * 100)
    per_task_score = round(100 / total)
    for t in derived_tasks:
        t["score"] = per_task_score if t.get("completed", False) else 0
    return overall_score, completed, total


def _detect_mode(submission: dict) -> str:
    """
    Returns "terminal" or "scenario".
    Terminal mode: terminal_history is non-empty list OR engine_response.exit_code is not None.
    Scenario mode: everything else.
    """
    history = submission.get("terminal_history") or []
    er = submission.get("engine_response") or {}
    if (isinstance(history, list) and len(history) > 0) or er.get("exit_code") is not None:
        return "terminal"
    return "scenario"


# ─────────────────────────────────────────────────────────────
# Prompt builders
# ─────────────────────────────────────────────────────────────

def _build_terminal_user_prompt(question: dict, submission: dict) -> str:
    q = question
    s = submission
    vs = (s.get("validation_signals") or {})
    er = (s.get("engine_response") or {})

    # Cap terminal history to last 10 entries, each output capped at 300 chars
    history = s.get("terminal_history") or []
    history_lines = []
    for entry in history[-10:]:
        cmd = str(entry.get("command") or "")
        out = str(entry.get("output") or "")[:300]
        history_lines.append(f"$ {cmd}\n{out}")
    history_block = "\n".join(history_lines) or "(empty)"

    return (
        f"question_id: {q.get('id', '')}\n"
        f"title: {q.get('title', '')}\n"
        f"description: {str(q.get('description', ''))[:600]}\n"
        f"instructions: {str(q.get('instructions', ''))[:400]}\n"
        f"constraints: {q.get('constraints', [])}\n"
        f"expected_submission_contains: {q.get('expected_submission_contains', [])}\n"
        f"expected_exit_code: {q.get('expected_exit_code')}\n\n"
        f"terminal_history (last 10 commands):\n{history_block}\n\n"
        f"engine_response:\n"
        f"  exit_code: {er.get('exit_code')}\n"
        f"  stdout: {str(er.get('stdout', ''))[:300]}\n"
        f"  stderr: {str(er.get('stderr', ''))[:200]}\n\n"
        f"validation_signals:\n"
        f"  passed: {vs.get('passed', False)}\n"
        f"  question_score: {vs.get('question_score')}\n"
        f"  max_score: {vs.get('max_score')}\n"
        f"  reasons: {vs.get('reasons', [])}\n\n"
        f"Return ONLY the JSON described in the system prompt."
    )


def _build_scenario_user_prompt(question: dict, submission: dict) -> str:
    q = question
    s = submission
    vs = (s.get("validation_signals") or {})
    answer = str(s.get("answer") or "")[:1500]

    return (
        f"question_id: {q.get('id', '')}\n"
        f"title: {q.get('title', '')}\n"
        f"description: {str(q.get('description', ''))[:600]}\n"
        f"instructions: {str(q.get('instructions', ''))[:400]}\n"
        f"constraints: {q.get('constraints', [])}\n"
        f"hints: {q.get('hints', [])}\n\n"
        f"candidate_answer:\n{answer}\n\n"
        f"validation_signals:\n"
        f"  passed: {vs.get('passed', False)}\n"
        f"  reasons: {vs.get('reasons', [])}\n\n"
        f"Return ONLY the JSON described in the system prompt."
    )


# ─────────────────────────────────────────────────────────────
# Response normalization
# ─────────────────────────────────────────────────────────────

def _normalize_response(raw: dict, validation_signals: dict | None = None) -> dict:
    """
    Maps Qwen's raw output to the full ai_feedback contract.
    Never raises — every field has a safe default.
    """
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
    if isinstance(raw_tasks, list):
        for t in raw_tasks:
            if not isinstance(t, dict):
                continue
            derived_tasks.append({
                "task":      _str(t.get("task"), 200),
                "score":     0,  # filled by _compute_scores
                "completed": bool(t.get("completed", False)),
                "evidence":  _str(t.get("evidence"), 300),
                "reasoning": _str(t.get("reasoning"), 200),
            })

    overall_score, completed_count, total_count = _compute_scores(derived_tasks)
    base["derived_tasks"] = derived_tasks
    base["overall_score"] = overall_score

    # task_completion mirrors the scoring
    base["task_completion"] = {
        "score":     overall_score,
        "comments":  _str(raw.get("feedback_summary"), 300),
        "completed": completed_count,
        "total":     total_count,
        "details":   [t["task"] for t in derived_tasks if t["completed"]],
    }

    # Narrative fields
    base["feedback_summary"]     = _str(raw.get("feedback_summary"), 500)
    base["one_liner"]            = _str(raw.get("one_liner"), 200)
    base["ideal_answer_summary"] = _str(raw.get("ideal_answer_summary"), 500)

    # List fields
    base["strengths"]               = _list_of_str(raw.get("strengths"))
    base["areas_for_improvement"]   = _list_of_str(raw.get("areas_for_improvement"))
    base["suggestions"]             = _list_of_str(raw.get("suggestions"))
    base["improvement_suggestions"] = _list_of_str(raw.get("improvement_suggestions") or raw.get("suggestions"))
    base["deduction_reasons"]       = _list_of_str(raw.get("deduction_reasons"))

    # Scored sub-objects — LLM may or may not provide these; default to 0
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
    """Deterministic fallback when Qwen fails."""
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

def get_devops_feedback(
    *,
    payload: dict,
    usage_meta: dict | None,
    route: str = "devops_evaluation",
) -> dict:
    """
    Main entry point called by the route handler.
    Accepts raw dict payload (validated by Pydantic at route level).
    Returns ai_feedback dict matching the Aaptor contract.
    route parameter allows Cloud_Evaluator to pass "cloud_evaluation" for billing.
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
        logger.info("[DEVOPS_EVAL] empty submission for question_id=%s", question_id)
        emit_eval_usage(usage_meta, route, latency_ms=0, cache_hit=False)
        return _empty_response()

    # Cache lookup
    cache_key = _cache_key(question_id, submission)
    if use_cache and cache_key in _cache:
        logger.info("[DEVOPS_EVAL] cache hit question_id=%s", question_id)
        emit_eval_usage(usage_meta, route, latency_ms=0, cache_hit=True)
        return _cache[cache_key]

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
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.1, max_tokens=900)
        latency_ms = (time.time() - start) * 1000

        parsed = safe_parse(raw)
        if parsed.get("parse_error") is True:
            raise ValueError(f"safe_parse returned parse_error: {parsed.get('overall_summary', '')[:200]}")

        result = _normalize_response(parsed, vs)
        emit_eval_usage(usage_meta, route, latency_ms=latency_ms, cache_hit=False)

    except Exception as e:
        logger.warning("[DEVOPS_EVAL] Qwen failed for question_id=%s: %s", question_id, str(e))
        emit_eval_usage(
            usage_meta,
            route,
            latency_ms=0,
            status="error",
            error_detail=str(e),
        )
        result = _fallback_response(vs)

    _cache[cache_key] = result
    return result
