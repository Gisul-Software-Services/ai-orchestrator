"""Design AI Evaluator — Option B: Rule-Based + Qwen Text Analysis.

Architecture:
  1. Rule-Based Evaluation  (shape counts, design system metrics — deterministic)
  2. Qwen Text Analysis     (deliverable coverage, design quality from metrics)
  3. Final score = (rule_score × 0.6) + (qwen_score × 0.4)

Rule-based scoring mirrors Aaptor's DesignEvaluationEngine exactly:
  - Component Count & Quality  (20 pts) — shape count vs difficulty thresholds
  - Layout Complexity          (15 pts) — pages, grid, shape density
  - Design Completeness        (15 pts) — deliverables coverage
  - Visual Hierarchy           (20 pts) — typography scales + colors
  - Professional Execution     (15 pts) — reusable components
  - Design System Thinking     (15 pts) — tokens, grid, components, palette

Qwen evaluates:
  - Deliverable completion quality (not just count)
  - Design system coherence
  - Constraint adherence
  - Actionable feedback text

Response contract matches Aaptor's ai_feedback shape with design-specific fields added.
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

# ─────────────────────────────────────────────────────────────
# Difficulty thresholds (shape count benchmarks from Aaptor)
# ─────────────────────────────────────────────────────────────

_THRESHOLDS = {
    "beginner":     {"excellent": 15, "good": 10, "moderate": 7,  "limited": 4},
    "intermediate": {"excellent": 30, "good": 20, "moderate": 15, "limited": 8},
    "advanced":     {"excellent": 40, "good": 30, "moderate": 20, "limited": 10},
}

_RULE_WEIGHT = 0.6
_QWEN_WEIGHT = 0.4


# ─────────────────────────────────────────────────────────────
# Rule-Based Scoring (100 pts total)
# ─────────────────────────────────────────────────────────────

def _shape_tier(total_elements: int, difficulty: str) -> str:
    """Returns 'excellent' | 'good' | 'moderate' | 'limited' | 'empty'."""
    if total_elements == 0:
        return "empty"
    t = _THRESHOLDS.get(difficulty, _THRESHOLDS["intermediate"])
    if total_elements >= t["excellent"]:
        return "excellent"
    if total_elements >= t["good"]:
        return "good"
    if total_elements >= t["moderate"]:
        return "moderate"
    if total_elements >= t["limited"]:
        return "limited"
    return "minimal"


def _tier_multiplier(tier: str) -> float:
    return {"excellent": 1.0, "good": 0.75, "moderate": 0.5,
            "limited": 0.25, "minimal": 0.1, "empty": 0.0}.get(tier, 0.0)


def _score_component_count(metrics: dict, difficulty: str) -> float:
    """Component Count & Quality — 20 pts."""
    n = metrics.get("total_elements", 0)
    if n == 0:
        return 0.0
    if n <= 2:
        return 0.5
    if n <= 4:
        return 2.0
    tier = _shape_tier(n, difficulty)
    return round(20 * _tier_multiplier(tier), 2)


def _score_layout_complexity(metrics: dict, difficulty: str) -> float:
    """Layout Complexity — 15 pts."""
    n = metrics.get("total_elements", 0)
    pages = metrics.get("pages", 1)
    has_grid = bool(metrics.get("has_grid", False))

    if n == 0:
        return 0.0
    if n <= 2:
        return 0.5
    if n <= 4:
        return 1.5

    tier = _shape_tier(n, difficulty)
    base = 15 * _tier_multiplier(tier)

    # Bonus for multi-page and grid
    if pages > 1:
        base = min(15, base + 2)
    if has_grid:
        base = min(15, base + 2)

    return round(base, 2)


def _score_design_completeness(metrics: dict) -> float:
    """Design Completeness — 15 pts (deliverables coverage)."""
    found = metrics.get("deliverables_found", [])
    missing = metrics.get("deliverables_missing", [])
    total = len(found) + len(missing)

    if total == 0:
        # No deliverables defined — score on element count
        n = metrics.get("total_elements", 0)
        if n == 0:
            return 0.0
        return min(15, round(n * 0.5, 2))

    coverage = len(found) / total
    return round(15 * coverage, 2)


def _score_visual_hierarchy(metrics: dict, difficulty: str) -> float:
    """Visual Hierarchy — 20 pts."""
    n = metrics.get("total_elements", 0)
    typo = metrics.get("typography_scales", 0)
    colors = metrics.get("colors_used", 0)

    if n == 0:
        return 0.0
    if n <= 2:
        return 0.5
    if n <= 4:
        return 2.0

    tier = _shape_tier(n, difficulty)
    base = 20 * _tier_multiplier(tier)

    # Typography bonus (up to +3)
    if typo >= 3:
        base = min(20, base + 3)
    elif typo >= 2:
        base = min(20, base + 1.5)

    # Color bonus (up to +2)
    if colors >= 3:
        base = min(20, base + 2)
    elif colors >= 2:
        base = min(20, base + 1)

    return round(base, 2)


def _score_professional_execution(metrics: dict, difficulty: str) -> float:
    """Professional Execution — 15 pts."""
    n = metrics.get("total_elements", 0)
    reusable = metrics.get("reusable_components", metrics.get("components", 0))

    if n == 0:
        return 0.0
    if n <= 2:
        return 0.5
    if n <= 4:
        return 1.5

    tier = _shape_tier(n, difficulty)
    base = 15 * _tier_multiplier(tier)

    # Reusable component bonus (up to +3)
    bonus = min(3, reusable)
    base = min(15, base + bonus)

    return round(base, 2)


def _score_design_system(metrics: dict) -> float:
    """Design System Thinking — 15 pts."""
    score = 0.0
    if metrics.get("has_tokens", False):
        score += 5
    if metrics.get("has_grid", False):
        score += 3
    # Reusable components: 1pt each, capped at 4
    reusable = metrics.get("reusable_components", metrics.get("components", 0))
    score += min(4, reusable)
    # Color palette: +3 if 3+ colors
    palette = metrics.get("color_palette_size", metrics.get("colors_used", 0))
    if palette >= 3:
        score += 3
    return min(15.0, round(score, 2))


def _run_rule_based(metrics: dict, difficulty: str) -> dict:
    """
    Run all 6 rule-based categories.
    Returns {category_scores, rule_score, breakdown}.
    """
    scores = {
        "component_count":    _score_component_count(metrics, difficulty),
        "layout_complexity":  _score_layout_complexity(metrics, difficulty),
        "design_completeness": _score_design_completeness(metrics),
        "visual_hierarchy":   _score_visual_hierarchy(metrics, difficulty),
        "professional_execution": _score_professional_execution(metrics, difficulty),
        "design_system":      _score_design_system(metrics),
    }
    rule_score = round(sum(scores.values()), 2)
    rule_score = min(100.0, rule_score)
    return {"category_scores": scores, "rule_score": rule_score}


# ─────────────────────────────────────────────────────────────
# Qwen System Prompt
# ─────────────────────────────────────────────────────────────

_QWEN_SYSTEM_PROMPT = """You are a strict UI/UX design evaluator assessing a design submission based on quantitative metrics.

You do NOT have access to the visual screenshot. Evaluate based on the design data provided.

Scoring criteria (total 100 points):
- deliverable_coverage (30 pts): Are all required deliverables present? Score based on found vs missing.
- design_system_quality (25 pts): Design tokens, grid system, reusable components, color palette coherence.
- complexity_appropriateness (25 pts): Is the element count appropriate for the difficulty level and deliverables?
- constraint_adherence (20 pts): Do the metrics suggest the constraints were followed?

Return ONLY valid JSON — no markdown, no code fences, no explanation:
{"deliverable_coverage":{"score":0,"comments":"<specific observation about found vs missing deliverables>"},"design_system_quality":{"score":0,"comments":"<observation about tokens, grid, components, palette>"},"complexity_appropriateness":{"score":0,"comments":"<observation about element count vs difficulty>"},"constraint_adherence":{"score":0,"comments":"<observation about constraint compliance from metrics>"},"qwen_score":0,"feedback_summary":"<2-3 sentences on overall design quality from metrics>","one_liner":"<single sentence verdict>","ideal_answer_summary":"<what a complete submission would look like>","strengths":["<strength based on metrics>"],"areas_for_improvement":["<gap based on metrics>"],"suggestions":["<concrete actionable suggestion>"],"deliverable_assessment":[{"name":"<deliverable name>","status":"completed|partial|missing","comment":"<specific observation>"}]}

Rules:
- qwen_score = weighted sum: (deliverable_coverage × 0.30) + (design_system_quality × 0.25) + (complexity_appropriateness × 0.25) + (constraint_adherence × 0.20)
- Score each criterion 0-100 based strictly on the metrics provided.
- If total_elements < 5, cap qwen_score at 15.
- If total_elements < 10, cap qwen_score at 25.
- If total_elements < 20, cap qwen_score at 40.
- Keep each string under 150 characters.
- Max 4 items per list field."""


def _build_qwen_prompt(question: dict, metrics: dict) -> str:
    found = metrics.get("deliverables_found", [])
    missing = metrics.get("deliverables_missing", [])
    total_deliverables = len(found) + len(missing)
    coverage_pct = round(len(found) / total_deliverables * 100) if total_deliverables > 0 else 0

    return (
        f"question_id: {question.get('id', '')}\n"
        f"title: {question.get('title', '')}\n"
        f"description: {str(question.get('description', ''))[:500]}\n"
        f"role: {question.get('role', 'UI/UX Designer')}\n"
        f"difficulty: {question.get('difficulty', 'intermediate')}\n"
        f"required_deliverables: {question.get('deliverables', [])}\n"
        f"constraints: {question.get('constraints', [])}\n\n"
        f"DESIGN METRICS:\n"
        f"  total_elements: {metrics.get('total_elements', 0)}\n"
        f"  pages: {metrics.get('pages', 1)}\n"
        f"  colors_used: {metrics.get('colors_used', 0)}\n"
        f"  typography_scales: {metrics.get('typography_scales', 0)}\n"
        f"  components: {metrics.get('components', 0)}\n"
        f"  reusable_components: {metrics.get('reusable_components', 0)}\n"
        f"  has_grid: {metrics.get('has_grid', False)}\n"
        f"  has_tokens: {metrics.get('has_tokens', False)}\n"
        f"  color_palette_size: {metrics.get('color_palette_size', metrics.get('colors_used', 0))}\n\n"
        f"DELIVERABLE COVERAGE: {len(found)}/{total_deliverables} ({coverage_pct}%)\n"
        f"  found: {found}\n"
        f"  missing: {missing}\n\n"
        f"Return ONLY the JSON described in the system prompt."
    )


# ─────────────────────────────────────────────────────────────
# Response building
# ─────────────────────────────────────────────────────────────

def _empty_response() -> dict:
    return {
        "overall_score": 0,
        "rule_score": 0,
        "qwen_score": 0,
        "rule_weight": _RULE_WEIGHT,
        "qwen_weight": _QWEN_WEIGHT,
        "score_is_partial": False,
        "evaluation_flags": [],
        "feedback_summary": "",
        "one_liner": "",
        "snapshot": "",
        "category_scores": {
            "component_count": 0,
            "layout_complexity": 0,
            "design_completeness": 0,
            "visual_hierarchy": 0,
            "professional_execution": 0,
            "design_system": 0,
        },
        "deliverable_coverage":        {"score": 0, "comments": ""},
        "design_system_quality":       {"score": 0, "comments": ""},
        "complexity_appropriateness":  {"score": 0, "comments": ""},
        "constraint_adherence":        {"score": 0, "comments": ""},
        "deliverable_assessment": [],
        "strengths":              [],
        "areas_for_improvement":  [],
        "suggestions":            [],
        "improvement_suggestions": [],
        "ideal_answer_summary":   "",
        "ai_generated":           True,
        "ai_vision_available":    False,
    }


def _normalize_qwen(raw: dict, n_elements: int) -> dict:
    """Normalize Qwen output. Never raises."""
    if not isinstance(raw, dict) or raw.get("parse_error"):
        return {}

    def _str(v, max_len=400):
        return str(v)[:max_len] if v is not None else ""

    def _int_clamp(v, lo=0, hi=100):
        try:
            return max(lo, min(hi, int(v)))
        except Exception:
            return lo

    def _list_of_str(v, max_items=4):
        if not isinstance(v, list):
            return []
        return [str(x) for x in v[:max_items] if str(x).strip()]

    # Apply element count caps to qwen_score
    raw_qwen = _int_clamp(raw.get("qwen_score", 0))
    if n_elements < 5:
        raw_qwen = min(15, raw_qwen)
    elif n_elements < 10:
        raw_qwen = min(25, raw_qwen)
    elif n_elements < 20:
        raw_qwen = min(40, raw_qwen)

    result = {
        "qwen_score": raw_qwen,
        "feedback_summary":    _str(raw.get("feedback_summary"), 500),
        "one_liner":           _str(raw.get("one_liner"), 200),
        "ideal_answer_summary": _str(raw.get("ideal_answer_summary"), 500),
        "strengths":              _list_of_str(raw.get("strengths")),
        "areas_for_improvement":  _list_of_str(raw.get("areas_for_improvement")),
        "suggestions":            _list_of_str(raw.get("suggestions")),
        "improvement_suggestions": _list_of_str(raw.get("suggestions")),
    }

    for key in ("deliverable_coverage", "design_system_quality",
                "complexity_appropriateness", "constraint_adherence"):
        raw_sub = raw.get(key)
        if isinstance(raw_sub, dict):
            result[key] = {
                "score":    _int_clamp(raw_sub.get("score", 0)),
                "comments": _str(raw_sub.get("comments", ""), 300),
            }

    # Deliverable assessment
    raw_da = raw.get("deliverable_assessment") or []
    da = []
    if isinstance(raw_da, list):
        for item in raw_da[:10]:
            if isinstance(item, dict):
                status = str(item.get("status", "missing"))
                if status not in ("completed", "partial", "missing"):
                    status = "missing"
                da.append({
                    "name":    _str(item.get("name", ""), 100),
                    "status":  status,
                    "comment": _str(item.get("comment", ""), 200),
                })
    result["deliverable_assessment"] = da

    return result


def _fallback_response(rule_result: dict) -> dict:
    base = _empty_response()
    rule_score = rule_result.get("rule_score", 0)
    base["rule_score"]    = rule_score
    base["overall_score"] = round(rule_score * _RULE_WEIGHT)
    base["category_scores"] = rule_result.get("category_scores", base["category_scores"])
    base["score_is_partial"] = True
    base["evaluation_flags"] = ["ai_evaluation_unavailable"]
    base["feedback_summary"] = "Rule-based scoring applied. AI analysis unavailable."
    base["one_liner"] = "Partial evaluation — human review recommended."
    return base


# ─────────────────────────────────────────────────────────────
# Cache key
# ─────────────────────────────────────────────────────────────

def _cache_key(question_id: str, metrics: dict) -> str:
    payload = f"{question_id}:{json.dumps(metrics, sort_keys=True, default=str)}"
    return hashlib.md5(payload.encode()).hexdigest()


# ─────────────────────────────────────────────────────────────
# Public entry point
# ─────────────────────────────────────────────────────────────

def get_design_feedback(
    *,
    payload: dict,
    usage_meta: dict | None,
) -> dict:
    """
    Main entry point for Design evaluation.
    Accepts raw dict payload (validated by Pydantic at route level).

    Returns a response with:
      - rule_score: deterministic score from shape/metric analysis (0-100)
      - qwen_score: Qwen text analysis score (0-100)
      - overall_score: weighted combination (rule×0.6 + qwen×0.4)
      - category_scores: breakdown of 6 rule-based categories
      - deliverable_assessment: per-deliverable status from Qwen
      - feedback_summary, strengths, areas_for_improvement, suggestions
    """
    question = payload.get("question") or {}
    submission = payload.get("submission") or {}
    use_cache = bool(payload.get("use_cache", True))
    question_id = str(question.get("id") or "")
    difficulty = str(question.get("difficulty") or "intermediate").lower()
    metrics_raw = submission.get("design_metrics") or {}

    # Normalize metrics — handle both dict and Pydantic model dump
    if hasattr(metrics_raw, "model_dump"):
        metrics = metrics_raw.model_dump()
    elif isinstance(metrics_raw, dict):
        metrics = metrics_raw
    else:
        metrics = {}

    n_elements = int(metrics.get("total_elements", 0))

    # Cache lookup
    cache_key = _cache_key(question_id, metrics)
    if use_cache and cache_key in _cache:
        logger.info("[DESIGN_EVAL] cache hit question_id=%s", question_id)
        emit_eval_usage(usage_meta, "design_evaluation", latency_ms=0, cache_hit=True)
        return _cache[cache_key]

    # ── Step 1: Rule-based scoring (always runs) ──────────────────────────
    rule_result = _run_rule_based(metrics, difficulty)
    rule_score = rule_result["rule_score"]

    # ── Step 2: Qwen text analysis ────────────────────────────────────────
    messages = [
        {"role": "system", "content": _QWEN_SYSTEM_PROMPT},
        {"role": "user",   "content": _build_qwen_prompt(question, metrics)},
    ]

    try:
        start = time.time()
        raw, prompt_tokens, completion_tokens = _llm_chat_coder(messages=messages, temperature=0.1, max_tokens=800)
        latency_ms = (time.time() - start) * 1000

        parsed = safe_parse(raw)
        if parsed.get("parse_error") is True:
            raise ValueError(f"safe_parse error: {parsed.get('overall_summary', '')[:200]}")

        qwen_data = _normalize_qwen(parsed, n_elements)
        qwen_score = qwen_data.get("qwen_score", 0)

        # ── Step 3: Final score ───────────────────────────────────────────
        overall_score = round((rule_score * _RULE_WEIGHT) + (qwen_score * _QWEN_WEIGHT))
        overall_score = max(0, min(100, overall_score))

        result = _empty_response()
        result["rule_score"]    = rule_score
        result["qwen_score"]    = qwen_score
        result["overall_score"] = overall_score
        result["category_scores"] = rule_result["category_scores"]

        # Merge Qwen narrative fields
        for field in ("feedback_summary", "one_liner", "ideal_answer_summary",
                      "strengths", "areas_for_improvement", "suggestions",
                      "improvement_suggestions", "deliverable_assessment",
                      "deliverable_coverage", "design_system_quality",
                      "complexity_appropriateness", "constraint_adherence"):
            if field in qwen_data:
                result[field] = qwen_data[field]

        result["snapshot"] = result["one_liner"]
        result["ai_generated"] = True
        result["ai_vision_available"] = False

        emit_eval_usage(
            usage_meta,
            "design_evaluation",
            latency_ms=latency_ms,
            cache_hit=False,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )

    except Exception as e:
        logger.warning("[DESIGN_EVAL] Qwen failed for question_id=%s: %s", question_id, str(e))
        emit_eval_usage(
            usage_meta,
            "design_evaluation",
            latency_ms=0,
            status="error",
            error_detail=str(e),
        )
        result = _fallback_response(rule_result)

    _cache[cache_key] = result
    return result
