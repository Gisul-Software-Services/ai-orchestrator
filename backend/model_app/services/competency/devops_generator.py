"""
DevOps Question Generator
=========================
Two-pass generation to fit within 1024-token vLLM context:
  Pass 1 — title + description (3 rich paragraphs)
  Pass 2 — task_steps + validation_hints  (code mode)
         — task + evaluation_criteria     (scenario mode)

RAG retrieve provides topic/difficulty signal to guide Pass 1.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException

from backend.model_app.prompts.competency.devops import (
    DEVOPS_SYSTEM,
    DEVOPS_PASS1_SCHEMA,
    DEVOPS_PASS2_CODE_SCHEMA,
    DEVOPS_PASS2_SCENARIO_SCHEMA,
)
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.services.rag_client import retrieve as rag_retrieve
from backend.model_app.services.rag_client import retrieve_bulk as rag_retrieve_bulk

logger = logging.getLogger(__name__)


def _build_rag_context(entry: dict) -> str:
    """Extract topic signal from a RAG catalog entry."""
    if not entry:
        return ""
    parts = []
    if entry.get("title"):
        parts.append(entry["title"])
    if entry.get("context"):
        # Strip "You are..." / "You need..." — violates G2, just take the topic part
        ctx = entry["context"]
        for prefix in ("You are ", "You need to ", "You want to ", "Given the "):
            if ctx.startswith(prefix):
                ctx = ctx[len(prefix):]
                break
        parts.append(ctx[:120])
    if entry.get("tags"):
        parts.append(", ".join(entry["tags"][:4]))
    return " | ".join(parts)


async def _pass1(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    focus_area: str,
    topics: list[str],
    rag_context: str,
) -> dict:
    """Pass 1: generate title + description."""
    topics_str = ", ".join(topics) if topics else focus_area
    user_prompt = DEVOPS_PASS1_SCHEMA.format(
        mode=mode,
        job_role=job_role,
        experience_years=experience_years,
        difficulty=difficulty,
        focus_area=focus_area,
        topics=topics_str,
        rag_context=rag_context or focus_area,
    )
    messages = [
        {"role": "system", "content": DEVOPS_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    decoded, _, _ = _llm_chat_single(
        messages,
        temperature=0.75,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=600,
    )
    return extract_json(decoded)


async def _pass2_code(title: str, description: str, difficulty: str, focus_area: str) -> dict:
    """Pass 2 (code mode): generate task_steps + validation_hints."""
    user_prompt = DEVOPS_PASS2_CODE_SCHEMA.format(
        title=title,
        description=description,
        difficulty=difficulty,
        focus_area=focus_area,
    )
    messages = [
        {"role": "system", "content": "Return ONLY valid JSON. No markdown, no explanation. First character must be {."},
        {"role": "user", "content": user_prompt},
    ]
    decoded, _, _ = _llm_chat_single(
        messages,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=600,
    )
    return extract_json(decoded)


async def _pass2_scenario(title: str, description: str, difficulty: str, focus_area: str) -> dict:
    """Pass 2 (scenario mode): generate task + evaluation_criteria."""
    user_prompt = DEVOPS_PASS2_SCENARIO_SCHEMA.format(
        title=title,
        description=description,
        difficulty=difficulty,
        focus_area=focus_area,
    )
    messages = [
        {"role": "system", "content": "Return ONLY valid JSON. No markdown, no explanation. First character must be {."},
        {"role": "user", "content": user_prompt},
    ]
    decoded, _, _ = _llm_chat_single(
        messages,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=400,
    )
    return extract_json(decoded)


async def _generate_question(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    focus_area: str,
    topics: list[str],
    time_limit: int,
    rag_context: str = "",
) -> dict:
    """Full two-pass generation of a single DevOps question."""
    # Pass 1 — title + description
    p1 = await _pass1(
        mode=mode,
        job_role=job_role,
        experience_years=experience_years,
        difficulty=difficulty,
        focus_area=focus_area,
        topics=topics,
        rag_context=rag_context,
    )
    title = p1.get("title", "")
    description = p1.get("description", "")
    logger.info("DevOps Pass 1 done: '%s' (%s/%s)", title, mode, difficulty)

    # Pass 2 — tasks
    if mode == "code":
        p2 = await _pass2_code(title, description, difficulty, focus_area)
        result = {
            "title": title,
            "difficulty": difficulty.lower(),
            "mode": "code",
            "description": description,
            "task_steps": p2.get("task_steps", []),
            "validation_hints": p2.get("validation_hints", []),
            "focus_area": focus_area,
            "topics": topics,
            "time_limit_minutes": time_limit,
            "ai_generated": True,
            "model": "qwen",
        }
    else:
        p2 = await _pass2_scenario(title, description, difficulty, focus_area)
        result = {
            "title": title,
            "difficulty": difficulty.lower(),
            "mode": "scenario",
            "description": description,
            "task": p2.get("task", ""),
            "evaluation_criteria": p2.get("evaluation_criteria", []),
            "focus_area": focus_area,
            "topics": topics,
            "time_limit_minutes": time_limit,
            "ai_generated": True,
            "model": "qwen",
        }

    logger.info("DevOps Pass 2 done: '%s'", title)
    return result


async def generate_devops_question(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    focus_area: str,
    topics: list[str],
    time_limit: int,
    http_request=None,
) -> dict:
    """Single DevOps question generation."""
    rag_result = await rag_retrieve(
        competency="devops",
        topic=focus_area,
        difficulty=difficulty,
        concepts=topics,
        top_k=10,
    )
    rag_context = ""
    if rag_result and rag_result.get("matched"):
        rag_context = _build_rag_context(rag_result["matched"])
        logger.info("RAG guided devops: '%s'", rag_result["matched"].get("title", ""))
    else:
        logger.info("No RAG match for devops focus_area='%s'", focus_area)

    try:
        return await _generate_question(
            mode=mode,
            job_role=job_role,
            experience_years=experience_years,
            difficulty=difficulty,
            focus_area=focus_area,
            topics=topics,
            time_limit=time_limit,
            rag_context=rag_context,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DevOps generation failed: {str(e)}")


async def generate_devops_questions_bulk(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    focus_area: str,
    topics: list[str],
    time_limit: int,
    count: int,
    http_request=None,
):
    """Yield `count` different DevOps questions using bulk RAG + two-pass generation."""
    candidates = await rag_retrieve_bulk(
        competency="devops",
        topic=focus_area,
        difficulty=difficulty,
        concepts=topics,
        count=count,
    )
    logger.info("Bulk RAG returned %d devops candidates for %d requested", len(candidates), count)

    generated_count = 0
    seen_titles: set[str] = set()

    for i, candidate in enumerate(candidates):
        if generated_count >= count:
            break
        rag_context = _build_rag_context(candidate.get("matched", {}))
        try:
            result = await _generate_question(
                mode=mode,
                job_role=job_role,
                experience_years=experience_years,
                difficulty=difficulty,
                focus_area=focus_area,
                topics=topics,
                time_limit=time_limit,
                rag_context=rag_context,
            )
            title = result.get("title", "")
            if title in seen_titles:
                logger.warning("Duplicate title, skipping: '%s'", title)
                continue
            seen_titles.add(title)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("DevOps generation failed for question %d: %s", i + 1, e)

    # Fill remaining with pure generation
    while generated_count < count:
        try:
            result = await _generate_question(
                mode=mode,
                job_role=job_role,
                experience_years=experience_years,
                difficulty=difficulty,
                focus_area=focus_area,
                topics=topics,
                time_limit=time_limit,
                rag_context="",
            )
            title = result.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("DevOps pure generation failed for question %d: %s", generated_count + 1, e)
            break
