"""
DSA Question Generator — Aaptor-facing endpoint service.

Flow:
  1. Bulk RAG retrieve → get N different problems in one call
  2. For each problem: MODE 1 (reword title+description via Qwen)
  3. Stream results back as they're generated
"""
from __future__ import annotations

import logging
import random
import time
import uuid

from fastapi import HTTPException

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.core.app import _emit_usage_metering
from backend.model_app.prompts.competency.dsa import (
    DSA_REWORD_RULES,
    DSA_REWORD_SCHEMA,
    DSA_GENERATION_RULES,
    DSA_GENERATION_SCHEMA,
)
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.services.rag_client import retrieve as rag_retrieve
from backend.model_app.services.rag_client import retrieve_bulk as rag_retrieve_bulk

logger = logging.getLogger(__name__)


def _normalize_concepts(concepts) -> list[str]:
    if not concepts:
        return []
    if isinstance(concepts, str):
        return [c.strip() for c in concepts.split(",") if c.strip()]
    return list(concepts)


def _filter_starter_code(selected: dict, languages: list[str]) -> dict:
    all_code = selected.get("starter_code_langs", selected.get("starter_code", {}))
    if not isinstance(all_code, dict):
        return {}
    if not languages:
        return all_code
    return {
        lang: code
        for lang, code in all_code.items()
        if lang.lower() in [l.lower() for l in languages]
    }


def _build_response_mode1(selected: dict, reworded: dict, languages: list[str]) -> dict:
    """Build Aaptor-compatible response from RAG dataset + reworded title/description."""
    starter_code = _filter_starter_code(selected, languages)
    return {
        "title": reworded.get("title", selected.get("title", "")),
        "description": reworded.get("description", selected.get("problem_description", selected.get("description", ""))),
        "difficulty": str(selected.get("difficulty", "medium")).lower(),
        "examples": selected.get("examples", []),
        "constraints": selected.get("constraints", []),
        "languages": languages or list(starter_code.keys()),
        "starter_code": starter_code,
        "function_signature": selected.get("function_signature", {}),
        "public_testcases": selected.get("public_testcases", []),
        "hidden_testcases": selected.get("hidden_testcases", []),
        "ai_generated": True,
        "model": "qwen",
    }


def _build_response_mode2(generated: dict, languages: list[str]) -> dict:
    """Build Aaptor-compatible response from pure LLM generation."""
    starter_code = generated.get("starter_code", {})
    if languages:
        starter_code = {k: v for k, v in starter_code.items() if k.lower() in [l.lower() for l in languages]}
    return {
        "title": generated.get("title", ""),
        "description": generated.get("description", ""),
        "difficulty": str(generated.get("difficulty", "medium")).lower(),
        "examples": generated.get("examples", []),
        "constraints": generated.get("constraints", []),
        "languages": languages or list(starter_code.keys()),
        "starter_code": starter_code,
        "function_signature": generated.get("function_signature", {}),
        "public_testcases": generated.get("public_testcases", []),
        "hidden_testcases": generated.get("hidden_testcases", []),
        "ai_generated": True,
        "model": "qwen",
    }


async def _reword_problem(selected: dict, languages: list[str]) -> dict:
    """Reword a single problem using Qwen (MODE 1)."""
    from backend.model_app.services.dsa import _is_restricted_path_problem, _restricted_path_guardrails
    guardrails = _restricted_path_guardrails() if _is_restricted_path_problem(selected) else ""

    user_prompt = DSA_REWORD_SCHEMA.format(
        title=selected.get("title", selected.get("task_id", "")),
        description=selected.get("problem_description", selected.get("description", ""))[:600],
        guardrails=guardrails,
    )

    try:
        messages = [
            {"role": "system", "content": DSA_REWORD_RULES},
            {"role": "user", "content": user_prompt},
        ]
        decoded, _, _ = _llm_chat_single(
            messages,
            temperature=0.75,
            top_p=0.9,
            repetition_penalty=1.1,
            max_tokens=600,
        )
        reworded = extract_json(decoded)
    except Exception as e:
        logger.warning("Reword failed: %s — using original", e)
        reworded = {
            "title": selected.get("title", ""),
            "description": selected.get("problem_description", selected.get("description", "")),
        }

    return _build_response_mode1(selected, reworded, languages)


async def _generate_pure(difficulty: str, topic: str, concepts_str: str, languages: list[str]) -> dict:
    """Generate a question from scratch using Qwen (MODE 2 fallback)."""
    languages_str = ", ".join(languages) if languages else "python, javascript"
    messages = [
        {"role": "system", "content": DSA_GENERATION_RULES},
        {"role": "user", "content": DSA_GENERATION_SCHEMA.format(
            topic=topic,
            concepts=concepts_str,
            difficulty=difficulty,
            languages=languages_str,
        )},
    ]
    decoded, _, _ = _llm_chat_single(
        messages,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=1200,
    )
    generated = extract_json(decoded)
    return _build_response_mode2(generated, languages)


async def generate_dsa_questions_bulk(
    difficulty: str,
    topic: str,
    concepts,
    languages: list[str],
    count: int = 1,
    http_request=None,
):
    """
    Generator that yields `count` different DSA questions sequentially.
    Uses bulk RAG retrieve to get all candidates in one call, then rewords each.
    """
    concepts_list = _normalize_concepts(concepts)
    concepts_str = ", ".join(concepts_list) if concepts_list else topic

    # Single bulk RAG call to get all candidates
    candidates = await rag_retrieve_bulk(
        competency="dsa",
        topic=topic,
        difficulty=difficulty.capitalize(),
        concepts=concepts_list,
        count=count,
    )

    logger.info("Bulk RAG returned %d candidates for %d requested", len(candidates), count)

    generated_count = 0

    # Reword each RAG candidate
    for i, candidate in enumerate(candidates):
        if generated_count >= count:
            break
        selected = candidate.get("matched", {})
        if not selected:
            continue
        try:
            result = await _reword_problem(selected, languages)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("Failed to reword problem %d: %s", i, e)

    # If RAG didn't return enough, fill with pure generation
    while generated_count < count:
        try:
            result = await _generate_pure(difficulty, topic, concepts_str, languages)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("Pure generation failed for question %d: %s", generated_count + 1, e)
            break


async def generate_dsa_question(
    difficulty: str,
    topic: str,
    concepts,
    languages: list[str],
    http_request=None,
    exclude_titles: list[str] | None = None,
) -> dict:
    """Single question generation — used when count=1."""
    concepts_list = _normalize_concepts(concepts)
    concepts_str = ", ".join(concepts_list) if concepts_list else topic

    rag_result = await rag_retrieve(
        competency="dsa",
        topic=topic,
        difficulty=difficulty.capitalize(),
        concepts=concepts_list,
        top_k=20,
    )

    # Skip if already used
    if rag_result and rag_result.get("matched") and exclude_titles:
        if rag_result["matched"].get("title", "") in exclude_titles:
            rag_result = None

    try:
        if rag_result and rag_result.get("matched"):
            return await _reword_problem(rag_result["matched"], languages)
        else:
            return await _generate_pure(difficulty, topic, concepts_str, languages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qwen generation failed: {str(e)}")
