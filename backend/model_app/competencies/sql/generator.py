"""
SQL Question Generator — Aaptor-facing endpoint service.

Flow:
  1. Bulk RAG retrieve → get N different SQL problems in one call
  2. For each problem: reword title + description via Qwen
  3. Return full structured response (schemas, sample_data, reference_query intact)
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import HTTPException

from backend.model_app.competencies.sql.prompts import SQL_REWORD_RULES, SQL_REWORD_SCHEMA
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single
from backend.model_app.services.rag_client import retrieve as rag_retrieve
from backend.model_app.services.rag_client import retrieve_bulk as rag_retrieve_bulk

logger = logging.getLogger(__name__)


def _build_response(selected: dict, reworded: dict) -> dict:
    """Build Aaptor-compatible SQL response from RAG dataset + reworded title/description."""
    return {
        "title": reworded.get("title", selected.get("title", "")),
        "description": reworded.get("description", selected.get("description", "")),
        "difficulty": str(selected.get("difficulty", "medium")).lower(),
        "question_type": "SQL",
        "sql_category": selected.get("sql_category", ""),
        "schemas": selected.get("schemas", {}),
        "sample_data": selected.get("sample_data", {}),
        "starter_query": selected.get("starter_query", "-- Write your SQL query here\n\nSELECT "),
        "reference_query": selected.get("reference_query", ""),
        "sql_expected_output": selected.get("sql_expected_output", ""),
        "hints": selected.get("hints", []),
        "evaluation": selected.get("evaluation", {
            "engine": "postgres",
            "comparison": "result_set",
            "order_sensitive": False,
        }),
        "constraints": selected.get("constraints", []),
        "ai_generated": True,
        "model": "qwen",
    }


async def _reword_problem(selected: dict) -> dict:
    """Reword title + description using Qwen."""
    # Extract table names from schemas so the prompt can enforce them
    schemas = selected.get("schemas", {})
    tables = ", ".join(schemas.keys()) if schemas else "see description"

    user_prompt = SQL_REWORD_SCHEMA.format(
        title=selected.get("title", ""),
        description=selected.get("description", "")[:600],
        tables=tables,
    )
    try:
        messages = [
            {"role": "system", "content": SQL_REWORD_RULES},
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
        logger.warning("SQL reword failed: %s — using original", e)
        reworded = {
            "title": selected.get("title", ""),
            "description": selected.get("description", ""),
        }
    return _build_response(selected, reworded)


async def generate_sql_questions_bulk(
    difficulty: str,
    topic: str,
    sql_category: Optional[str],
    count: int = 1,
    http_request=None,
):
    """Generator that yields `count` SQL questions sequentially via bulk RAG + reword."""
    concepts = [sql_category] if sql_category else []

    candidates = await rag_retrieve_bulk(
        competency="sql",
        topic=topic,
        difficulty=difficulty.capitalize(),
        concepts=concepts,
        count=count,
    )

    logger.info("SQL bulk RAG returned %d candidates for %d requested", len(candidates), count)

    generated_count = 0
    for i, candidate in enumerate(candidates):
        if generated_count >= count:
            break
        selected = candidate.get("matched", {})
        if not selected:
            continue
        try:
            result = await _reword_problem(selected)
            result["question_index"] = generated_count + 1
            result["total"] = count
            generated_count += 1
            yield result
        except Exception as e:
            logger.error("Failed to reword SQL problem %d: %s", i, e)


async def generate_sql_question(
    difficulty: str,
    topic: str,
    sql_category: Optional[str],
    http_request=None,
) -> dict:
    """Single SQL question generation."""
    concepts = [sql_category] if sql_category else []

    rag_result = await rag_retrieve(
        competency="sql",
        topic=topic,
        difficulty=difficulty.capitalize(),
        concepts=concepts,
        top_k=20,
    )

    if rag_result and rag_result.get("matched"):
        try:
            return await _reword_problem(rag_result["matched"])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"SQL reword failed: {str(e)}")

    raise HTTPException(
        status_code=404,
        detail=f"No SQL problem found for topic='{topic}' difficulty='{difficulty}'"
    )
