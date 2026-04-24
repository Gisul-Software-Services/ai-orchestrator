"""Shared LLM client + billing for evaluation.

This module intentionally mirrors the `services/model.py` vLLM calling pattern,
but uses a separate coder model instance (`state.coder_llm`) so evaluation
traffic is tracked separately in billing.
"""

from __future__ import annotations

import json
import logging
import time
from uuid import uuid4

from vllm import LLM, SamplingParams

from backend.model_app.billing.metering import current_token_counts, schedule_usage_emit
from backend.model_app.core import state as app_state
from backend.model_app.core.settings import get_settings

logger = logging.getLogger(__name__)


def _make_sampling_params(
    *,
    temperature: float,
    max_tokens: int,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
) -> SamplingParams:
    return SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        repetition_penalty=repetition_penalty,
    )


def _ensure_coder_loaded() -> LLM:
    llm = getattr(app_state, "coder_llm", None)
    if llm is not None:
        return llm

    s = get_settings()
    mn = s.coder_model_name
    # If generation model already loaded and matches coder model, reuse it.
    gen = getattr(app_state, "llm", None)
    if gen is not None and (mn or "").strip() == (s.model_name or "").strip():
        app_state.coder_llm = gen
        return gen

    logger.info("Loading coder model %s with vLLM AWQ...", mn)
    app_state.coder_llm = LLM(
        model=mn,
        quantization="awq",
        dtype="float16",
        gpu_memory_utilization=s.vllm_gpu_memory_utilization,
        max_model_len=s.vllm_max_model_len,
        max_num_seqs=s.vllm_max_num_seqs,
        trust_remote_code=True,
    )
    return app_state.coder_llm


def _llm_chat_coder(
    messages: list[dict[str, str]],
    temperature: float = 0.2,
    max_tokens: int = 600,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
) -> tuple[str, int, int]:
    """
    Calls Qwen Coder model for evaluation tasks.
    Returns (response_text, prompt_tokens, completion_tokens) and updates
    `current_token_counts` for billing.
    """
    llm = _ensure_coder_loaded()
    sampling_params = _make_sampling_params(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        repetition_penalty=repetition_penalty,
    )

    t0 = time.perf_counter()
    outputs = llm.chat(messages=messages, sampling_params=sampling_params, use_tqdm=False)
    out = outputs[0]
    text = out.outputs[0].text.strip() if out.outputs else ""
    prompt_tokens = len(getattr(out, "prompt_token_ids", []) or [])
    completion_tokens = len(getattr(out.outputs[0], "token_ids", []) or []) if out.outputs else 0

    try:
        current_token_counts.set(
            {
                "prompt_tokens": max(0, int(prompt_tokens)),
                "completion_tokens": max(0, int(completion_tokens)),
                "total_tokens": max(0, int(prompt_tokens) + int(completion_tokens)),
            }
        )
    except Exception:
        pass

    _ = t0  # keep local timing parity with generation call sites
    return text, int(prompt_tokens), int(completion_tokens)


def emit_eval_usage(
    usage_meta: dict | None,
    route: str,
    latency_ms: float,
    cache_hit: bool = False,
    status: str = "success",
    error_detail: str | None = None,
) -> None:
    """
    Emit billing for an evaluation call.
    Uses `coder_model_name` so usage_logs records correct model for eval traffic.
    """
    # Ensure token counters are not stale on cache hits / errors.
    # (Usage rows should reflect 0 tokens when no model call happened.)
    try:
        if cache_hit or status != "success":
            current_token_counts.set({"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0})
    except Exception:
        pass

    s = get_settings()
    schedule_usage_emit(
        job_id=str(uuid4()),
        usage_meta=usage_meta,
        route=route,
        cache_hit=cache_hit,
        latency_ms=latency_ms,
        status=status,
        error_detail=error_detail,
        model_name=s.coder_model_name,
    )


def safe_parse(raw: str) -> dict:
    """Best-effort JSON object extraction for LLM outputs.

    The model sometimes returns extra text around the JSON (or wraps it in fences).
    We try strict parse first, then fall back to extracting the first balanced
    JSON object substring.
    """

    def _strip_fences(s: str) -> str:
        s = (s or "").strip()
        if s.startswith("```"):
            # Keep only the first fenced block content if present.
            parts = s.split("```")
            if len(parts) >= 3:
                s = parts[1]
                s = s.lstrip()
                if s.startswith("json"):
                    s = s[4:]
        return s.strip().rstrip("```").strip()

    def _extract_first_json_object(s: str) -> str | None:
        # Find the first balanced {...} substring, respecting strings/escapes.
        start = s.find("{")
        if start < 0:
            return None
        in_str = False
        esc = False
        depth = 0
        for i in range(start, len(s)):
            ch = s[i]
            if in_str:
                if esc:
                    esc = False
                elif ch == "\\":
                    esc = True
                elif ch == '"':
                    in_str = False
                continue
            if ch == '"':
                in_str = True
                continue
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        return None

    clean = _strip_fences(raw)

    # 1) Strict JSON parse
    try:
        v = json.loads(clean)
        return v if isinstance(v, dict) else {"overall_summary": clean, "parse_error": True}
    except Exception:
        pass

    # 2) Extract first JSON object
    extracted = _extract_first_json_object(clean)
    if extracted:
        try:
            v = json.loads(extracted)
            return v if isinstance(v, dict) else {"overall_summary": clean, "parse_error": True}
        except Exception:
            return {"overall_summary": clean, "parse_error": True}

    # 3) Fallback: parse between first "{" and last "}" (handles extra braces in text)
    try:
        start = clean.find("{")
        end = clean.rfind("}")
        if start >= 0 and end > start:
            candidate = clean[start : end + 1]
            v = json.loads(candidate)
            return v if isinstance(v, dict) else {"overall_summary": clean, "parse_error": True}
    except Exception:
        pass

    return {"overall_summary": clean, "parse_error": True}

