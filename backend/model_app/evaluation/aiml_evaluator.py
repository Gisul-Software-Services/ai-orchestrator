from __future__ import annotations

import hashlib
import json
import logging
import time

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=500, ttl=3600)

# NOTE: AIML evaluation is Python-first in this deployment. We intentionally
# treat submissions as Python to keep the prompt + validation simple.
_DEFAULT_LANGUAGE = "python"

_PRODUCT_SYSTEM_PROMPT = """You are evaluating an AIML submission.

Return ONLY ONE JSON object with EXACTLY these top-level keys (no extra keys):
overall_score, feedback_summary, one_liner, task_scores, task_completion,
code_quality, library_usage, output_quality, strengths, areas_for_improvement,
suggestions, deduction_reasons, ai_generated

Rules:
- Output MUST be MINIFIED JSON (no markdown, no code fences, no newlines/indentation).
- Include ALL keys always. Use empty strings/lists where needed.
- task_scores: list of objects with keys: task_number, task_description, score, max_score, status, feedback.
- task_completion: object with keys: completed, total, details.
- code_quality/library_usage/output_quality: objects with keys: score, comments.
- Be concise and specific. No praise fluff.
- Do NOT reveal hidden testcase details or hidden expected outputs (only counts).
- Judge ONLY from provided source_code + outputs + task/test metadata; do not pretend to execute code.
- Output must end with '}' and contain nothing after it.
"""


def get_aiml_feedback_product_contract(*, payload: dict, usage_meta: dict | None) -> dict:
    """
    Accepts Aaptor EvaluateSubmissionRequest payload and returns the expected AIML evaluation response.
    Uses Qwen coder model under the hood; evaluates only from provided code + outputs.
    """
    code = str(payload.get("source_code") or "")
    language = _DEFAULT_LANGUAGE

    title = str(payload.get("question_title") or "")
    desc = str(payload.get("question_description") or "")
    tasks = payload.get("tasks") or []
    constraints = payload.get("constraints") or []
    difficulty = str(payload.get("difficulty") or "")
    skill = payload.get("skill")
    dataset_info = payload.get("dataset_info") or {}
    outputs = payload.get("outputs") or []
    test_cases = payload.get("test_cases") or []

    # Cache key based on stable evaluation inputs.
    cache_key = hashlib.md5(
        f"{title}:{language}:{code}:{json.dumps(outputs, sort_keys=True, default=str)[:2000]}".encode()
    ).hexdigest()
    if cache_key in _cache:
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    if not code or len(code.strip()) < 20:
        fb = _product_empty()
        _cache[cache_key] = fb
        return fb

    def _truncate(s: str, n: int) -> str:
        s = s or ""
        return s if len(s) <= n else s[:n] + "…"

    # Build compact prompt content to fit small context budgets.
    task_lines = "\n".join(f"- {i+1}. {str(t)[:160]}" for i, t in enumerate(tasks[:6])) or "None"
    constraint_lines = "\n".join(f"- {str(c)[:160]}" for c in constraints[:4]) or "None"

    tc_lines = []
    if isinstance(test_cases, list):
        for tc in test_cases[:8]:
            if not isinstance(tc, dict):
                continue
            tc_lines.append(
                f"- task_number={tc.get('task_number')} "
                f"validation_type={tc.get('validation_type')} "
                f"points={tc.get('points')} "
                f"description={_truncate(str(tc.get('description') or ''), 140)}"
            )
    tc_block = "\n".join(tc_lines) if tc_lines else "None"

    out_block = ""
    if isinstance(outputs, list) and outputs:
        joined = "\n---\n".join(_truncate(str(x), 220) for x in outputs[:4])
        out_block = joined
    else:
        out_block = "None"

    user_prompt = (
        f"question_title: {title}\n"
        f"question_description: {_truncate(desc, 500)}\n"
        f"difficulty: {difficulty}\n"
        f"skill: {skill}\n"
        f"language: {language}\n\n"
        f"tasks:\n{task_lines}\n\n"
        f"constraints:\n{constraint_lines}\n\n"
        f"dataset_info (summary): {_truncate(json.dumps(dataset_info, default=str) if isinstance(dataset_info, dict) else str(dataset_info), 250)}\n\n"
        f"test_cases (metadata only):\n{tc_block}\n\n"
        f"outputs (execution logs/metrics):\n{out_block}\n\n"
        f"candidate_submission:\n```python\n{_truncate(code, 2000)}\n```\n\n"
        f"Return ONLY the minified JSON described in the system prompt."
    )

    messages = [
        {"role": "system", "content": _PRODUCT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        start = time.time()
        # Keep output budget bounded; prompt is compact and output is minified JSON.
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=450)
        latency_ms = (time.time() - start) * 1000
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=latency_ms, cache_hit=False)
        out = safe_parse(raw)
        fb = _normalize_product(out)
    except Exception as e:
        emit_eval_usage(usage_meta, "aiml_evaluation", latency_ms=0, status="error", error_detail=str(e))
        fb = _product_empty()

    _cache[cache_key] = fb
    return fb


def _product_empty() -> dict:
    return {
        "overall_score": 0,
        "feedback_summary": "",
        "one_liner": "",
        "task_scores": [],
        "task_completion": {"completed": 0, "total": 0, "details": []},
        "code_quality": {"score": 0, "comments": ""},
        "library_usage": {"score": 0, "comments": ""},
        "output_quality": {"score": 0, "comments": ""},
        "strengths": [],
        "areas_for_improvement": [],
        "suggestions": [],
        "deduction_reasons": [],
        "ai_generated": True,
    }


def _normalize_product(raw: dict) -> dict:
    base = _product_empty()
    if not isinstance(raw, dict):
        return base

    # If the model did not return valid product JSON, `safe_parse` returns
    # {"overall_summary": <raw_text>, "parse_error": True}. In that case, avoid
    # returning a completely empty contract: surface a short parse hint in the
    # allowed fields so callers can diagnose issues.
    if raw.get("parse_error") is True:
        summary = str(raw.get("overall_summary") or "").strip()
        if summary:
            summary = summary[:800] + ("…" if len(summary) > 800 else "")
            base["feedback_summary"] = summary
            base["one_liner"] = "Evaluation output was not valid JSON; please retry."
            base["deduction_reasons"] = ["EVALUATION_PARSE_ERROR"]
        return base

    # Copy only known keys to enforce contract.
    for k in list(base.keys()):
        if k in raw:
            base[k] = raw[k]

    def _to_int(v, default: int = 0) -> int:
        try:
            if isinstance(v, bool):
                return default
            return int(v)
        except Exception:
            return default

    def _clamp_int(v: int, lo: int, hi: int) -> int:
        return lo if v < lo else hi if v > hi else v

    def _norm_status(v) -> str:
        s = str(v or "").strip().lower().replace("-", "_").replace(" ", "_")
        # Common model variants
        if s in {"completed", "complete", "done", "success"}:
            return "completed"
        if s in {"partially_completed", "partial", "partially_complete", "incomplete"}:
            return "partially_completed"
        if s in {"attempted_incorrect", "incorrect", "wrong", "failed"}:
            return "attempted_incorrect"
        if s in {"not_attempted", "not_completed", "notcomplete", "na", "n_a"}:
            return "not_attempted"
        # Default to not_attempted when unknown
        return "not_attempted"

    # Ensure types
    if not isinstance(base.get("task_scores"), list):
        base["task_scores"] = []
    if not isinstance(base.get("task_completion"), dict):
        base["task_completion"] = {"completed": 0, "total": 0, "details": []}

    # Normalize task_completion.details to list[str]
    tc = base.get("task_completion") or {}
    if isinstance(tc, dict):
        details = tc.get("details")
        if isinstance(details, str):
            tc["details"] = [details] if details.strip() else []
        elif isinstance(details, list):
            tc["details"] = [str(x) for x in details if str(x).strip()]
        else:
            tc["details"] = []
        tc["completed"] = _clamp_int(_to_int(tc.get("completed"), 0), 0, 10_000)
        tc["total"] = _clamp_int(_to_int(tc.get("total"), 0), 0, 10_000)
        base["task_completion"] = tc

    # Normalize task_scores entries to the contract shape.
    norm_scores: list[dict] = []
    for i, item in enumerate(base.get("task_scores") or []):
        if not isinstance(item, dict):
            continue
        task_number = _to_int(item.get("task_number"), i + 1)
        task_desc = str(item.get("task_description") or "").strip()
        score = _to_int(item.get("score"), 0)
        max_score = _to_int(item.get("max_score"), 10)
        max_score = _clamp_int(max_score, 1, 10)
        score = _clamp_int(score, 0, max_score)
        status = _norm_status(item.get("status"))
        feedback = str(item.get("feedback") or "").strip()
        norm_scores.append(
            {
                "task_number": task_number,
                "task_description": task_desc,
                "score": score,
                "max_score": max_score,
                "status": status,
                "feedback": feedback,
            }
        )
    base["task_scores"] = norm_scores

    # Normalize top-level overall_score to 0-100 int.
    base["overall_score"] = _clamp_int(_to_int(base.get("overall_score"), 0), 0, 100)

    for k in ("code_quality", "library_usage", "output_quality"):
        if not isinstance(base.get(k), dict):
            base[k] = {"score": 0, "comments": ""}
        else:
            base[k].setdefault("score", 0)
            base[k].setdefault("comments", "")
            base[k]["score"] = _clamp_int(_to_int(base[k].get("score"), 0), 0, 100)
            base[k]["comments"] = str(base[k].get("comments") or "")

    for arr in ("strengths", "areas_for_improvement", "suggestions", "deduction_reasons"):
        if not isinstance(base.get(arr), list):
            base[arr] = []
        else:
            base[arr] = [str(x) for x in base[arr] if str(x).strip()]

    # Ensure ai_generated is true for this LLM path.
    base["ai_generated"] = True
    return base

