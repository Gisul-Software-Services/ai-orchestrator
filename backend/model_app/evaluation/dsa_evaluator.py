from __future__ import annotations

import hashlib
import logging
import time

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=500, ttl=3600)

SUPPORTED_LANGS = {
    "python", "c", "cpp", "java", "javascript",
    "typescript", "go", "rust", "kotlin", "csharp",
}

# ─────────────────────────────────────────────────────────────
# Redesigned system prompt — 0-100 scale, compact, clear formula
# ─────────────────────────────────────────────────────────────

_PRODUCT_SYSTEM_PROMPT = """You are a strict DSA code evaluator. Score on a 0-100 scale.

Scoring formula:
  overall_score = round((test_score × 0.60) + (code_quality.score × 0.25) + (correctness.score × 0.15))
  where test_score = round((total_passed / total_tests) × 100)  [provided in the prompt]

Return ONLY valid JSON — no markdown, no code fences, no explanation:
{"overall_score":0,"feedback_summary":"<2 sentences>","one_liner":"<single sentence>","code_quality":{"score":0,"comments":"<specific comment on code structure, naming, idioms>"},"efficiency":{"time_complexity":"<O(...)>","space_complexity":"<O(...)>","comments":"<1 sentence>"},"correctness":{"score":0,"comments":"<comment on correctness based on test results>"},"suggestions":["<suggestion>"],"strengths":["<strength>"],"areas_for_improvement":["<area>"],"deduction_reasons":["<reason>"],"improvement_suggestions":["<suggestion>"]}

Rules:
- overall_score MUST be 0-100 (not 0-10).
- Use the test_score formula above as the primary driver.
- code_quality.score and correctness.score are also 0-100.
- If code is empty or < 20 chars, set all scores to 0.
- Do NOT reveal hidden test case inputs/outputs. Refer to hidden failures by count only.
- Max 4 items per list field.
- feedback_summary must be 3-4 sentences covering: what works, what doesn't, complexity analysis, and one specific improvement.
- Keep each string under 200 characters."""


def _build_user_prompt(
    title: str,
    desc: str,
    language: str,
    code: str,
    starter: str,
    total_passed: int,
    total_tests: int,
    public_passed: int,
    public_total: int,
    hidden_passed: int,
    hidden_total: int,
    failed_public: list[dict],
    time_spent,
    lang_rules: str,
    lang_edges: str,
) -> str:
    test_score = round((total_passed / total_tests) * 100) if total_tests > 0 else 0
    hidden_fail = max(0, hidden_total - hidden_passed)

    def _summarize_case(tc: dict) -> str:
        inp = str(tc.get("input") or "")[:200]
        exp = str(tc.get("expected_output") or "")[:200]
        out = str(tc.get("user_output") or "")[:200]
        err = str(tc.get("stderr") or tc.get("compile_output") or "")[:200]
        return f"  input: {inp}\n  expected: {exp}\n  got: {out}" + (f"\n  error: {err}" if err else "")

    failed_block = "\n".join(_summarize_case(tc) for tc in failed_public[:2]) or "None"

    desc_short = desc[:400]
    code_short = code[:600]
    starter_short = (starter or "")[:200]

    return (
        f"question: {title}\n"
        f"description: {desc_short}\n"
        f"language: {language}\n\n"
        f"test_results:\n"
        f"  test_score (for formula): {test_score}/100\n"
        f"  total: {total_passed}/{total_tests} passed\n"
        f"  public: {public_passed}/{public_total}\n"
        f"  hidden: {hidden_passed}/{hidden_total} ({hidden_fail} hidden failures)\n\n"
        f"failed_public_cases (max 2):\n{failed_block}\n\n"
        f"language_rules:\n{lang_rules}\n"
        f"edge_cases_to_check:\n{lang_edges}\n\n"
        + (f"starter_code:\n{starter_short}\n\n" if starter_short.strip() else "")
        + f"source_code:\n```{language}\n{code_short}\n```\n\n"
        f"Apply the scoring formula from the system prompt. Return ONLY JSON."
    )


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_dsa_feedback_product_contract(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Redesigned DSA evaluator.
    - overall_score on 0-100 scale
    - Compact prompt fits within 1024 token context
    - Score formula: test_score(60%) + code_quality(25%) + correctness(15%)
    - Supported languages: python, c, cpp, java, javascript, typescript, go, rust, kotlin, csharp
    """
    code = str(payload.get("source_code") or "")
    language = str(payload.get("language") or "").strip().lower()
    if language not in SUPPORTED_LANGS:
        language = "python"

    title = str(payload.get("question_title") or "")
    desc = str(payload.get("question_description") or "")
    starter = payload.get("starter_code")

    total_passed = int(payload.get("total_passed") or 0)
    total_tests = int(payload.get("total_tests") or 0)
    public_passed = int(payload.get("public_passed") or 0)
    public_total = int(payload.get("public_total") or 0)
    hidden_passed = int(payload.get("hidden_passed") or 0)
    hidden_total = int(payload.get("hidden_total") or 0)
    time_spent = payload.get("time_spent_seconds")

    # Collect failed public test cases (max 2)
    test_results = payload.get("test_results") or []
    failed_public: list[dict] = []
    if isinstance(test_results, list):
        for row in test_results:
            if not isinstance(row, dict):
                continue
            if not bool(row.get("passed", False)) and not bool(row.get("hidden", False) or row.get("is_hidden", False)):
                failed_public.append(row)
            if len(failed_public) >= 2:
                break

    # Cache key
    cache_key = hashlib.md5(
        f"{title}:{language}:{code}:{public_passed}:{public_total}:{hidden_passed}:{hidden_total}".encode()
    ).hexdigest()

    if cache_key in _cache:
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=0, cache_hit=True)
        cached = _cache[cache_key]
        return _with_meta(cached, public_passed, public_total, hidden_passed, hidden_total)

    # Short-circuit on empty code
    if not code or len(code.strip()) < 20:
        fb = _product_empty()
        _cache[cache_key] = fb
        return _with_meta(fb, public_passed, public_total, hidden_passed, hidden_total)

    lang_rules, lang_edges = _language_guidance(language)
    user_prompt = _build_user_prompt(
        title=title, desc=desc, language=language, code=code,
        starter=starter if isinstance(starter, str) else "",
        total_passed=total_passed, total_tests=total_tests,
        public_passed=public_passed, public_total=public_total,
        hidden_passed=hidden_passed, hidden_total=hidden_total,
        failed_public=failed_public, time_spent=time_spent,
        lang_rules=lang_rules, lang_edges=lang_edges,
    )

    messages = [
        {"role": "system", "content": _PRODUCT_SYSTEM_PROMPT},
        {"role": "user",   "content": user_prompt},
    ]

    try:
        start = time.time()
        raw, prompt_tokens, completion_tokens = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=900)
        latency_ms = (time.time() - start) * 1000
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=latency_ms, cache_hit=False,
                        prompt_tokens=prompt_tokens, completion_tokens=completion_tokens)

        out = safe_parse(raw)
        if out.get("parse_error"):
            raise ValueError(f"safe_parse error: {out.get('overall_summary', '')[:200]}")

        fb = _normalize_product(out, total_passed, total_tests)

    except Exception as e:
        logger.warning("[DSA_EVAL] Qwen failed: %s", str(e))
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=0, status="error", error_detail=str(e))
        fb = _product_fallback(total_passed, total_tests, public_passed, public_total, hidden_passed, hidden_total)

    _cache[cache_key] = fb
    return _with_meta(fb, public_passed, public_total, hidden_passed, hidden_total)


# ─────────────────────────────────────────────────────────────
# Normalization — enforce 0-100 scale and scoring formula
# ─────────────────────────────────────────────────────────────

def _normalize_product(raw: dict, total_passed: int, total_tests: int) -> dict:
    base = _product_empty()
    if not isinstance(raw, dict):
        return base

    def _int_clamp(v, lo=0, hi=100):
        try:
            return max(lo, min(hi, int(float(v))))
        except Exception:
            return lo

    def _str(v, max_len=300):
        return str(v)[:max_len] if v is not None else ""

    def _list_of_str(v, max_items=2):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v[:max_items] if str(x).strip()]

    # Sub-scores — Qwen may return 0-10 or 0-100, normalize to 0-100
    def _to_100(v) -> int:
        val = _int_clamp(v, 0, 100)
        if val <= 10:
            val = val * 10
        return val

    cq_score = _to_100((raw.get("code_quality") or {}).get("score", 0))
    corr_score = _to_100((raw.get("correctness") or {}).get("score", 0))

    # Recompute overall_score using the formula — don't trust Qwen's value
    test_score = round((total_passed / total_tests) * 100) if total_tests > 0 else 0
    overall = round((test_score * 0.60) + (cq_score * 0.25) + (corr_score * 0.15))
    overall = max(0, min(100, overall))

    base["overall_score"]    = overall
    base["feedback_summary"] = _str(raw.get("feedback_summary"), 500)
    base["one_liner"]        = _str(raw.get("one_liner"), 200)

    base["code_quality"] = {
        "score":    cq_score,
        "comments": _str((raw.get("code_quality") or {}).get("comments", ""), 300),
    }
    base["correctness"] = {
        "score":    corr_score,
        "comments": _str((raw.get("correctness") or {}).get("comments", ""), 300),
    }

    eff = raw.get("efficiency") or {}
    base["efficiency"] = {
        "time_complexity":  _str(eff.get("time_complexity", ""), 50),
        "space_complexity": _str(eff.get("space_complexity", ""), 50),
        "comments":         _str(eff.get("comments", ""), 200),
    }

    base["suggestions"]             = _list_of_str(raw.get("suggestions"), 4)
    base["strengths"]               = _list_of_str(raw.get("strengths"), 4)
    base["areas_for_improvement"]   = _list_of_str(raw.get("areas_for_improvement"), 4)
    base["deduction_reasons"]       = _list_of_str(raw.get("deduction_reasons"), 4)
    base["improvement_suggestions"] = _list_of_str(raw.get("improvement_suggestions") or raw.get("suggestions"), 4)

    return base


def _with_meta(fb: dict, public_passed: int, public_total: int, hidden_passed: int, hidden_total: int) -> dict:
    out = dict(fb)
    out["ai_generated"] = True
    out["test_breakdown"] = {
        "public_passed":  public_passed,
        "public_total":   public_total,
        "hidden_passed":  hidden_passed,
        "hidden_total":   hidden_total,
    }
    return out


def _product_empty() -> dict:
    return {
        "overall_score": 0,
        "feedback_summary": "",
        "one_liner": "",
        "code_quality":  {"score": 0, "comments": ""},
        "efficiency":    {"time_complexity": "", "space_complexity": "", "comments": ""},
        "correctness":   {"score": 0, "comments": ""},
        "suggestions":             [],
        "strengths":               [],
        "areas_for_improvement":   [],
        "deduction_reasons":       [],
        "improvement_suggestions": [],
    }


def _product_fallback(
    total_passed: int, total_tests: int,
    public_passed: int, public_total: int,
    hidden_passed: int, hidden_total: int,
) -> dict:
    test_score = round((total_passed / total_tests) * 100) if total_tests > 0 else 0
    hidden_fail = max(0, hidden_total - hidden_passed)
    base = _product_empty()
    base["overall_score"]    = test_score
    base["feedback_summary"] = f"Public: {public_passed}/{public_total}. Hidden failures: {hidden_fail}. AI analysis unavailable."
    base["one_liner"]        = "Evaluation unavailable — human review recommended."
    return base


# ─────────────────────────────────────────────────────────────
# Language guidance
# ─────────────────────────────────────────────────────────────

def _language_guidance(language: str) -> tuple[str, str]:
    if language == "python":
        return (
            "- Clarity, correctness, Python idioms.\n- Check None handling, bounds, recursion depth.",
            "- Empty input, single element.\n- None/missing keys.\n- Negative values.",
        )
    if language in ("c", "cpp"):
        return (
            "- Memory safety: bounds, null pointers, uninitialized vars.\n- Integer overflow, signed/unsigned bugs.",
            "- Null pointers, empty arrays.\n- Buffer bounds, off-by-one.\n- Overflow.",
        )
    if language == "java":
        return (
            "- Null handling, collections usage, complexity.\n- Avoid unnecessary object creation.",
            "- Null inputs.\n- Empty arrays.\n- Integer overflow.",
        )
    if language in ("javascript", "typescript"):
        return (
            "- Type coercion, undefined/null edge cases.\n- Mutation vs immutability.",
            "- undefined/null inputs.\n- NaN.\n- Array bounds.",
        )
    if language == "go":
        return (
            "- nil slices/maps, bounds, error handling.\n- Avoid unnecessary allocations.",
            "- nil vs empty slices.\n- Map key missing.\n- Bounds.",
        )
    if language == "rust":
        return (
            "- Ownership/borrowing, safe indexing.\n- Avoid panics on indexing.",
            "- Safe vs panicking indexing.\n- Empty inputs.\n- Overflow.",
        )
    if language == "kotlin":
        return (
            "- Null-safety, idiomatic collections.\n- Avoid excessive allocations.",
            "- Nullability.\n- Empty collections.\n- Overflow.",
        )
    if language == "csharp":
        return (
            "- Null handling, collection bounds, LINQ performance.\n- Avoid heavy allocations in loops.",
            "- null inputs.\n- Empty arrays.\n- Overflow.",
        )
    return (
        "- Evaluate correctness, complexity, code clarity.",
        "- Empty input, edge values, bounds.",
    )
