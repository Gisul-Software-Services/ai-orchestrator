from __future__ import annotations

import hashlib
import logging
import time

from cachetools import TTLCache

from backend.model_app.evaluation.base import _llm_chat_coder, emit_eval_usage, safe_parse

logger = logging.getLogger(__name__)

_cache = TTLCache(maxsize=500, ttl=3600)

SUPPORTED_LANGS = {
    "python",
    "c",
    "cpp",
    "java",
    "javascript",
    "typescript",
    "go",
    "rust",
    "kotlin",
    "csharp",
}

_SYSTEM_PROMPT = """You are a senior software engineer reviewing a DSA coding submission.

Return ONLY valid JSON, no markdown, no explanation:
{
  "overall_summary": "<2 sentences>",
  "time_complexity": { "value": "<O(...)>", "explanation": "<1 sentence>" },
  "space_complexity": { "value": "<O(...)>", "explanation": "<1 sentence>" },
  "code_quality": {
    "score": <1-10>,
    "issues": ["<issue>"],
    "positives": ["<positive>"]
  },
  "suggestions": ["<suggestion 1>", "<suggestion 2>"],
  "edge_cases_missed": ["<edge case>"]
}

Rules:
- Be concise and specific
- Do not praise unnecessarily
- If code is empty or gibberish return score 0
- Max 2 suggestions, max 2 edge cases
"""

_PRODUCT_SYSTEM_PROMPT = """You are a strict technical code evaluator.

Return ONLY valid JSON matching exactly this schema (no markdown, no extra keys):
{
  "overall_score": 0,
  "feedback_summary": "",
  "one_liner": "",
  "code_quality": { "score": 0, "comments": "" },
  "efficiency": { "time_complexity": "", "space_complexity": "", "comments": "" },
  "correctness": { "score": 0, "comments": "" },
  "suggestions": [],
  "strengths": [],
  "areas_for_improvement": [],
  "deduction_reasons": [],
  "improvement_suggestions": []
}

Rules:
- Be concise and specific.
- No praise fluff.
- Do NOT reveal hidden testcases. You may refer to hidden failures only by count.
"""


def get_dsa_feedback(
    *,
    code: str,
    language: str,
    problem_title: str,
    problem_id: str,
    test_results: dict,
    score: int,
    usage_meta: dict | None,
) -> dict:
    cache_key = hashlib.md5(f"{problem_id}:{language}:{code}".encode()).hexdigest()
    if cache_key in _cache:
        logger.info("[DSA_EVAL] cache hit problem_id=%s", problem_id)
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    if not code or len(code.strip()) < 20:
        fb = _empty()
        _cache[cache_key] = fb
        return fb

    user_msg = (
        f"Problem: {problem_title}\n"
        f"Language: {language}\n"
        f"Score: {score}/100\n"
        f"Tests passed: {test_results.get('passed', 0)}/{test_results.get('total', 0)}\n\n"
        f"Code:\n```{language}\n{code}\n```"
    )
    messages = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_msg},
    ]

    try:
        start = time.time()
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.2, max_tokens=600)
        latency_ms = (time.time() - start) * 1000
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=latency_ms, cache_hit=False)
        feedback = safe_parse(raw)
    except Exception as e:
        logger.error("[DSA_EVAL] coder model failed: %s", str(e))
        emit_eval_usage(
            usage_meta,
            "dsa_evaluation",
            latency_ms=0,
            status="error",
            error_detail=str(e),
        )
        feedback = _fallback(test_results, score)

    _cache[cache_key] = feedback
    return feedback


def get_dsa_feedback_product_contract(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Accepts the Aaptor-style feedback payload and returns the expected response contract.
    Uses Qwen coder model under the hood.
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

    test_results = payload.get("test_results") or []
    failed_public: list[dict] = []
    if isinstance(test_results, list):
        for row in test_results:
            if not isinstance(row, dict):
                continue
            passed = bool(row.get("passed", False))
            is_hidden = bool(row.get("hidden", False) or row.get("is_hidden", False))
            if not passed and not is_hidden:
                failed_public.append(row)
            if len(failed_public) >= 3:
                break

    def _summarize_case(tc: dict) -> str:
        inp = tc.get("input")
        exp = tc.get("expected_output")
        out = tc.get("user_output")
        err = tc.get("stderr") or tc.get("compile_output") or ""
        return (
            f"- input: {inp}\n"
            f"  expected_output: {exp}\n"
            f"  user_output: {out}\n"
            f"  error: {str(err)[:400] if err else ''}"
        )

    failed_public_block = "\n".join(_summarize_case(tc) for tc in failed_public) if failed_public else "None"

    lang_rules, lang_edges = _language_guidance(language)
    user_prompt = (
        f"question_title: {title}\n"
        f"question_description: {desc[:2500]}\n\n"
        f"language: {language}\n"
        f"evaluation_rules_for_language:\n{lang_rules}\n\n"
        f"common_edge_cases_for_language:\n{lang_edges}\n\n"
        f"time_spent_seconds: {payload.get('time_spent_seconds')}\n\n"
        f"test_summary:\n"
        f"- total_passed/total_tests: {total_passed}/{total_tests}\n"
        f"- public_passed/public_total: {public_passed}/{public_total}\n"
        f"- hidden_passed/hidden_total: {hidden_passed}/{hidden_total}\n"
        f"- hidden_failures: {max(0, hidden_total - hidden_passed)}\n\n"
        f"failed_public_testcases (max 3):\n{failed_public_block}\n\n"
        f"starter_code:\n{starter if isinstance(starter, str) else ''}\n\n"
        f"source_code:\n```{language}\n{code}\n```\n\n"
        f"Return ONLY the JSON schema described in the system prompt."
    )

    cache_key = hashlib.md5(f"{title}:{language}:{code}:{public_passed}:{public_total}:{hidden_passed}:{hidden_total}".encode()).hexdigest()
    if cache_key in _cache:
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=0, cache_hit=True)
        cached = _cache[cache_key]
        return _with_meta(cached, public_passed, public_total, hidden_passed, hidden_total)

    if not code or len(code.strip()) < 20:
        fb = _product_empty()
        _cache[cache_key] = fb
        return _with_meta(fb, public_passed, public_total, hidden_passed, hidden_total)

    messages = [
        {"role": "system", "content": _PRODUCT_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    try:
        start = time.time()
        raw, _, _ = _llm_chat_coder(messages=messages, temperature=0.0, max_tokens=900)
        latency_ms = (time.time() - start) * 1000
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=latency_ms, cache_hit=False)
        out = safe_parse(raw)
        fb = _normalize_product(out)
    except Exception as e:
        emit_eval_usage(usage_meta, "dsa_evaluation", latency_ms=0, status="error", error_detail=str(e))
        fb = _product_fallback(public_passed, public_total, hidden_passed, hidden_total)

    _cache[cache_key] = fb
    return _with_meta(fb, public_passed, public_total, hidden_passed, hidden_total)


def _with_meta(fb: dict, public_passed: int, public_total: int, hidden_passed: int, hidden_total: int) -> dict:
    out = dict(fb)
    out["ai_generated"] = True
    out["test_breakdown"] = {
        "public_passed": public_passed,
        "public_total": public_total,
        "hidden_passed": hidden_passed,
        "hidden_total": hidden_total,
    }
    return out


def _normalize_product(raw: dict) -> dict:
    base = _product_empty()
    if not isinstance(raw, dict):
        return base
    for k in base.keys():
        if k in raw:
            base[k] = raw[k]
    # Ensure nested structures
    for k in ("code_quality", "efficiency", "correctness"):
        if not isinstance(base.get(k), dict):
            base[k] = _product_empty()[k]
    for arr_key in (
        "suggestions",
        "strengths",
        "areas_for_improvement",
        "deduction_reasons",
        "improvement_suggestions",
    ):
        if not isinstance(base.get(arr_key), list):
            base[arr_key] = []
    return base


def _language_guidance(language: str) -> tuple[str, str]:
    """Short, structured language-specific guidance for higher-quality feedback."""
    if language == "python":
        return (
            "- Focus on clarity, correctness, and Python idioms.\n"
            "- Check for None handling, list/dict bounds, recursion depth, and integer overflow not applicable.\n"
            "- Prefer simple, readable solutions unless constraints demand optimization.",
            "- Empty input, single element.\n"
            "- None / missing keys.\n"
            "- Index/bounds errors.\n"
            "- Negative values if applicable.",
        )
    if language in ("c", "cpp"):
        return (
            "- Consider memory safety: bounds, null pointers, use-after-free, uninitialized variables.\n"
            "- Consider integer overflow, signed/unsigned bugs, and performance.\n"
            "- Verify correct data structure usage and complexity.",
            "- Null pointers / empty arrays.\n"
            "- Buffer/array bounds, off-by-one.\n"
            "- Uninitialized variables, overflow.\n"
            "- Segfault risk with invalid indices.",
        )
    if language == "java":
        return (
            "- Check for null handling, class/method structure, and correct use of collections.\n"
            "- Consider time/space complexity and edge cases.\n"
            "- Avoid unnecessary object creation in hot loops.",
            "- Null inputs.\n"
            "- Empty arrays/lists.\n"
            "- Off-by-one indices.\n"
            "- Integer overflow on sums/products.",
        )
    if language in ("javascript", "typescript"):
        return (
            "- Consider type coercion pitfalls and edge cases for undefined/null.\n"
            "- In TypeScript, check types and safe narrowing.\n"
            "- Watch for mutation vs immutability and performance for large inputs.",
            "- undefined/null inputs.\n"
            "- NaN / non-integer numbers.\n"
            "- Array bounds / empty arrays.\n"
            "- Large inputs performance.",
        )
    if language == "go":
        return (
            "- Check nil slices/maps, bounds, and error handling patterns.\n"
            "- Prefer simple loops; avoid unnecessary allocations.\n"
            "- Confirm complexity and correctness.",
            "- nil vs empty slices.\n"
            "- Map key missing cases.\n"
            "- Bounds/off-by-one.\n"
            "- Large inputs allocations.",
        )
    if language == "rust":
        return (
            "- Consider ownership/borrowing, mutability, and safe indexing.\n"
            "- Prefer iterators when clear; avoid panics on indexing.\n"
            "- Confirm correctness and complexity.",
            "- Safe vs panicking indexing.\n"
            "- Empty inputs.\n"
            "- Overflow with i32/i64.\n"
            "- Ownership/clone overhead.",
        )
    if language == "kotlin":
        return (
            "- Consider null-safety, idiomatic collections usage, and performance.\n"
            "- Avoid excessive allocations; confirm correctness and complexity.",
            "- Nullability edge cases.\n"
            "- Empty collections.\n"
            "- Off-by-one.\n"
            "- Overflow with Int/Long.",
        )
    if language == "csharp":
        return (
            "- Consider null handling, collection bounds, and LINQ performance pitfalls.\n"
            "- Confirm correctness and complexity; avoid heavy allocations in loops.",
            "- null inputs.\n"
            "- Empty arrays.\n"
            "- Off-by-one.\n"
            "- Overflow on int arithmetic.",
        )
    return (
        "- Evaluate correctness, complexity, and code clarity.",
        "- Empty input, edge values, bounds.",
    )


def _product_empty() -> dict:
    return {
        "overall_score": 0,
        "feedback_summary": "",
        "one_liner": "",
        "code_quality": {"score": 0, "comments": ""},
        "efficiency": {"time_complexity": "", "space_complexity": "", "comments": ""},
        "correctness": {"score": 0, "comments": ""},
        "suggestions": [],
        "strengths": [],
        "areas_for_improvement": [],
        "deduction_reasons": [],
        "improvement_suggestions": [],
    }


def _product_fallback(public_passed: int, public_total: int, hidden_passed: int, hidden_total: int) -> dict:
    hidden_fail = max(0, hidden_total - hidden_passed)
    return {
        "overall_score": 0,
        "feedback_summary": f"Public passed {public_passed}/{public_total}. Hidden failures: {hidden_fail}.",
        "one_liner": "Evaluation unavailable; manual review required.",
        "code_quality": {"score": 0, "comments": ""},
        "efficiency": {"time_complexity": "", "space_complexity": "", "comments": ""},
        "correctness": {"score": 0, "comments": ""},
        "suggestions": [],
        "strengths": [],
        "areas_for_improvement": [],
        "deduction_reasons": [],
        "improvement_suggestions": [],
    }

def _empty() -> dict:
    return {
        "overall_summary": "No code submitted.",
        "time_complexity": {"value": "N/A", "explanation": ""},
        "space_complexity": {"value": "N/A", "explanation": ""},
        "code_quality": {"score": 0, "issues": ["Empty submission"], "positives": []},
        "suggestions": [],
        "edge_cases_missed": [],
    }


def _fallback(test_results: dict, score: int) -> dict:
    passed = test_results.get("passed", 0)
    total = test_results.get("total", 0)
    return {
        "overall_summary": f"Passed {passed}/{total} test cases. Score: {score}/100.",
        "time_complexity": {"value": "Unknown", "explanation": "Analysis unavailable"},
        "space_complexity": {"value": "Unknown", "explanation": "Analysis unavailable"},
        "code_quality": {"score": round(score / 10), "issues": [], "positives": []},
        "suggestions": ["Review failed test cases and check edge conditions."],
        "edge_cases_missed": [],
    }

