"""
Cloud (AWS) Question Generator
================================
Two-pass generation to fit within 1024-token vLLM context:
  Pass 1 — title + description (3 rich paragraphs)
  Pass 2 — task_steps + validation_hints  (code mode)
         — task + evaluation_criteria     (scenario mode)

RAG catalog provides AWS service/concept/core_idea as topic signal.
Qwen always generates the full rich question — RAG guides the topic only.
"""
from __future__ import annotations

import logging

from fastapi import HTTPException

from backend.model_app.competencies.cloud.prompts import (
    CLOUD_SYSTEM,
    CLOUD_PASS1_SCHEMA,
    CLOUD_PASS2_CODE_SCHEMA,
    CLOUD_PASS2_SCENARIO_SCHEMA,
)
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.services.rag_client import retrieve as rag_retrieve
from backend.model_app.services.rag_client import retrieve_bulk as rag_retrieve_bulk

logger = logging.getLogger(__name__)


def _build_rag_context(entry: dict) -> str:
    """
    Extract topic signal from a cloud RAG catalog entry.
    Cloud entries have: service, action, concept, core_idea.
    """
    if not entry:
        return ""
    parts = []
    if entry.get("service"):
        parts.append(f"Service: {entry['service'].upper()}")
    if entry.get("concept"):
        parts.append(f"Concept: {entry['concept']}")
    if entry.get("core_idea"):
        parts.append(f"Core idea: {entry['core_idea']}")
    if entry.get("action"):
        parts.append(f"Action: {entry['action']}")
    return " | ".join(parts)


async def _pass1(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    aws_service: str,
    concepts: list[str],
    time_limit: int,
    rag_context: str,
) -> dict:
    """Pass 1: generate title + description."""
    concepts_str = ", ".join(concepts) if concepts else aws_service
    user_prompt = CLOUD_PASS1_SCHEMA.format(
        mode=mode,
        job_role=job_role,
        experience_years=experience_years,
        difficulty=difficulty,
        aws_service=aws_service.upper() if aws_service else "AWS",
        concepts=concepts_str,
        time_limit=time_limit,
        rag_context=rag_context or f"{aws_service} {difficulty}",
    )
    messages = [
        {"role": "system", "content": CLOUD_SYSTEM},
        {"role": "user", "content": user_prompt},
    ]
    decoded, _, _ = _llm_chat_single(
        messages,
        temperature=0.75,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=600,
    )
    logger.info(f"Cloud Pass 1 raw output length: {len(decoded)} chars")
    logger.info(f"Cloud Pass 1 raw output:\n{decoded}")
    return extract_json(decoded)


async def _pass2_code(
    title: str,
    description: str,
    difficulty: str,
    aws_service: str,
) -> dict:
    """Pass 2 (code mode): generate task_steps + validation_hints."""
    user_prompt = CLOUD_PASS2_CODE_SCHEMA.format(
        title=title,
        description=description,
        difficulty=difficulty,
        aws_service=aws_service.upper() if aws_service else "AWS",
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


async def _pass2_scenario(
    title: str,
    description: str,
    difficulty: str,
    aws_service: str,
) -> dict:
    """Pass 2 (scenario mode): generate task + evaluation_criteria."""
    user_prompt = CLOUD_PASS2_SCENARIO_SCHEMA.format(
        title=title,
        description=description,
        difficulty=difficulty,
        aws_service=aws_service.upper() if aws_service else "AWS",
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
    aws_service: str,
    concepts: list[str],
    time_limit: int,
    rag_context: str = "",
) -> dict:
    """Full two-pass generation of a single Cloud question."""
    # Pass 1 — title + description
    p1 = await _pass1(
        mode=mode,
        job_role=job_role,
        experience_years=experience_years,
        difficulty=difficulty,
        aws_service=aws_service,
        concepts=concepts,
        time_limit=time_limit,
        rag_context=rag_context,
    )
    title = p1.get("title", "")
    description = p1.get("description", "")
    logger.info("Cloud Pass 1 done: '%s' (%s/%s/%s)", title, aws_service, mode, difficulty)

    # Pass 2 — tasks
    if mode == "code":
        p2 = await _pass2_code(title, description, difficulty, aws_service)
        result = {
            "title": title,
            "difficulty": difficulty.lower(),
            "mode": "code",
            "description": description,
            "task_steps": p2.get("task_steps", []),
            "validation_hints": p2.get("validation_hints", []),
            "aws_service": aws_service,
            "concepts": concepts,
            "time_limit_minutes": time_limit,
            "ai_generated": True,
            "model": "qwen",
        }
    else:
        p2 = await _pass2_scenario(title, description, difficulty, aws_service)
        result = {
            "title": title,
            "difficulty": difficulty.lower(),
            "mode": "scenario",
            "description": description,
            "task": p2.get("task", ""),
            "evaluation_criteria": p2.get("evaluation_criteria", []),
            "aws_service": aws_service,
            "concepts": concepts,
            "time_limit_minutes": time_limit,
            "ai_generated": True,
            "model": "qwen",
        }

    logger.info("Cloud Pass 2 done: '%s'", title)
    return result


async def generate_cloud_question(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    aws_service: str,
    concepts: list[str],
    time_limit: int,
    http_request=None,
) -> dict:
    """Single Cloud question generation."""
    # RAG retrieve — cloud catalog has no difficulty field, filter by service/concept
    rag_result = await rag_retrieve(
        competency="cloud",
        topic=aws_service,
        difficulty=difficulty,
        concepts=concepts,
        top_k=10,
    )
    rag_context = ""
    if rag_result and rag_result.get("matched"):
        rag_context = _build_rag_context(rag_result["matched"])
        logger.info("RAG guided cloud: '%s'", rag_result["matched"].get("concept", ""))
    else:
        logger.info("No RAG match for cloud service='%s'", aws_service)

    try:
        return await _generate_question(
            mode=mode,
            job_role=job_role,
            experience_years=experience_years,
            difficulty=difficulty,
            aws_service=aws_service,
            concepts=concepts,
            time_limit=time_limit,
            rag_context=rag_context,
        )
    except Exception as e:
        logger.error(f"Cloud generation failed: {type(e).__name__}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Cloud generation failed: {str(e)}")


async def generate_cloud_questions_bulk(
    mode: str,
    job_role: str,
    experience_years: int,
    difficulty: str,
    aws_service: str,
    concepts: list[str],
    time_limit: int,
    count: int,
    http_request=None,
):
    """Yield `count` different Cloud questions using bulk RAG + two-pass generation."""
    candidates = await rag_retrieve_bulk(
        competency="cloud",
        topic=aws_service,
        difficulty=difficulty,
        concepts=concepts,
        count=count,
    )
    logger.info("Bulk RAG returned %d cloud candidates for %d requested", len(candidates), count)

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
                aws_service=aws_service,
                concepts=concepts,
                time_limit=time_limit,
                rag_context=rag_context,
            )
            title = result.get("title", "")
            if title in seen_titles:
                logger.warning("Duplicate cloud title, skipping: '%s'", title)
                continue
            seen_titles.add(title)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("Cloud generation failed for question %d: %s", i + 1, e)

    # Fill remaining with pure generation
    while generated_count < count:
        try:
            result = await _generate_question(
                mode=mode,
                job_role=job_role,
                experience_years=experience_years,
                difficulty=difficulty,
                aws_service=aws_service,
                concepts=concepts,
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
            logger.error("Cloud pure generation failed for question %d: %s", generated_count + 1, e)
            break
