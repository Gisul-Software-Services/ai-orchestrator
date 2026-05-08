"""SQL question generation route — Production Ready with Category Routing."""
from __future__ import annotations

import json
import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

import asyncio
import uuid

from backend.model_app.competencies.sql.schema import SQLQuestionRequest
from backend.model_app.competencies.sql import generator as sql_generator
from backend.model_app.competencies.sql import schema_generator
from backend.model_app.competencies.sql.category_router import route_category, get_supported_categories, is_supported
from backend.model_app.services.jobs import _job_store_set, _job_store_update

logger = logging.getLogger(__name__)

router = APIRouter(tags=["sql"])
sql_router = router


@router.post("/api/v1/generate-sql-question")
async def generate_sql_question(body: SQLQuestionRequest, http_request: Request):
    """
    Generate SQL question(s) with intelligent category routing.
    
    PRODUCTION READY:
    - Automatic routing based on category (RAG vs schema-based)
    - Fallback logic if primary path fails
    - Support for all SQL categories
    - Quality metrics tracking
    
    - count=1 : returns a single JSON object
    - count>1 : streams questions as NDJSON (one per line, sent as generated)
    """
    count = max(1, min(body.count, 20))
    
    # Determine category to use (sql_category takes precedence over topic)
    user_category = body.sql_category or body.topic
    
    # Route the category
    canonical_category, generation_path = route_category(user_category)
    
    logger.info(f"Request: category='{user_category}' → canonical='{canonical_category}', path='{generation_path}'")
    
    # Check if category is supported
    if generation_path == "unknown":
        supported = get_supported_categories()
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Category '{user_category}' is not supported",
                "canonical_category": canonical_category,
                "supported_categories": supported["all_supported"],
                "rag_supported": supported["rag_supported"],
                "schema_based": supported["schema_based"]
            }
        )
    
    if count == 1:
        return await _generate_single_question(
            body=body,
            http_request=http_request,
            canonical_category=canonical_category,
            generation_path=generation_path
        )
    
    # Streaming for multiple questions
    async def stream_questions():
        async for result in _generate_multiple_questions(
            body=body,
            http_request=http_request,
            canonical_category=canonical_category,
            generation_path=generation_path,
            count=count
        ):
            yield json.dumps(result) + "\n"
    
    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={
            "X-Total-Questions": str(count),
            "X-Category": canonical_category,
            "X-Generation-Path": generation_path
        },
    )


async def _generate_single_question(
    body: SQLQuestionRequest,
    http_request: Request,
    canonical_category: str,
    generation_path: str
):
    """
    Generate a single question with fallback logic.
    """
    # Try primary path
    try:
        if generation_path == "rag":
            # Use RAG catalog (fast, proven quality)
            return await sql_generator.generate_sql_question(
                difficulty=body.difficulty,
                topic=body.topic,
                sql_category=canonical_category,
                http_request=http_request,
            )
        else:  # schema
            # Use schema-based generation (flexible, unlimited)
            # Pass topic as domain so schema matches the requested subject area
            return await schema_generator.generate_question_from_schema(
                difficulty=body.difficulty,
                sql_category=canonical_category,
                domain=body.topic,
                http_request=http_request,
            )
    except HTTPException as e:
        # If primary path fails with 404, try fallback
        if e.status_code == 404 and generation_path == "rag":
            logger.warning(f"RAG path failed for '{canonical_category}', falling back to schema-based")
            try:
                result = await schema_generator.generate_question_from_schema(
                    difficulty=body.difficulty,
                    sql_category=canonical_category,
                    domain=None,
                    http_request=http_request,
                )
                result["generation_path"] = "schema_fallback"
                return result
            except Exception as fallback_error:
                logger.error(f"Fallback also failed: {fallback_error}")
                raise e  # Raise original error
        else:
            raise


async def _generate_multiple_questions(
    body: SQLQuestionRequest,
    http_request: Request,
    canonical_category: str,
    generation_path: str,
    count: int
):
    """
    Generate multiple questions with fallback logic.
    """
    generated = 0
    
    # Try primary path
    try:
        if generation_path == "rag":
            async for result in sql_generator.generate_sql_questions_bulk(
                difficulty=body.difficulty,
                topic=body.topic,
                sql_category=canonical_category,
                count=count,
                http_request=http_request,
            ):
                result["generation_path"] = "rag"
                generated += 1
                yield result
        else:  # schema
            async for result in schema_generator.generate_sql_questions_from_schema_bulk(
                difficulty=body.difficulty,
                sql_category=canonical_category,
                domain=body.topic,
                count=count,
                http_request=http_request,
            ):
                result["generation_path"] = "schema"
                generated += 1
                yield result
    except Exception as e:
        logger.error(f"Generation failed after {generated}/{count} questions: {e}")
        # If we generated some questions, that's OK
        if generated == 0:
            raise



@router.post("/api/v1/generate-sql-question-async")
async def generate_sql_question_async(body: SQLQuestionRequest, http_request: Request):
    """
    Async SQL question generation — returns job_id immediately.
    The generation runs behind the global LLM semaphore so it never
    interrupts evaluation requests and vice versa.

    Poll GET /api/v1/job/{job_id} for the result.

    Scaling: to allow N concurrent requests on N GPUs, set
    LLM_CONCURRENCY=N in environment variables.
    """
    from backend.model_app.core.state import llm_semaphore

    count = max(1, min(body.count, 20))
    user_category = body.sql_category or body.topic
    canonical_category, generation_path = route_category(user_category)

    if generation_path == "unknown":
        supported = get_supported_categories()
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Category '{user_category}' is not supported",
                "supported_categories": supported["all_supported"],
            }
        )

    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                # Run generation — semaphore ensures no GPU contention
                if count == 1:
                    if generation_path == "rag":
                        result = await sql_generator.generate_sql_question(
                            difficulty=body.difficulty,
                            topic=body.topic,
                            sql_category=canonical_category,
                            http_request=http_request,
                        )
                    else:
                        result = await schema_generator.generate_question_from_schema(
                            difficulty=body.difficulty,
                            sql_category=canonical_category,
                            domain=body.topic,
                            http_request=http_request,
                        )
                else:
                    results = []
                    if generation_path == "rag":
                        async for q in sql_generator.generate_sql_questions_bulk(
                            difficulty=body.difficulty,
                            topic=body.topic,
                            sql_category=canonical_category,
                            count=count,
                            http_request=http_request,
                        ):
                            q["generation_path"] = "rag"
                            results.append(q)
                    else:
                        async for q in schema_generator.generate_sql_questions_from_schema_bulk(
                            difficulty=body.difficulty,
                            sql_category=canonical_category,
                            domain=body.topic,
                            count=count,
                            http_request=http_request,
                        ):
                            q["generation_path"] = "schema"
                            results.append(q)
                    result = results

            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})

        except Exception as exc:
            logger.error(f"[SQL_GEN_ASYNC] job {job_id} failed: {exc}")
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


@router.post("/api/v1/generate-sql-question-from-schema")
async def generate_sql_question_from_schema(body: SQLQuestionRequest, http_request: Request):
    """
    Generate SQL question(s) dynamically from database schemas stored in MongoDB.
    
    DEPRECATED: Use /api/v1/generate-sql-question instead (it auto-routes to schema-based when needed)
    
    This endpoint is kept for backward compatibility.
    """
    count = max(1, min(body.count, 20))

    if count == 1:
        return await schema_generator.generate_question_from_schema(
            difficulty=body.difficulty,
            sql_category=body.sql_category or body.topic,
            domain=None,
            http_request=http_request,
        )

    async def stream_questions():
        async for result in schema_generator.generate_sql_questions_from_schema_bulk(
            difficulty=body.difficulty,
            sql_category=body.sql_category or body.topic,
            domain=None,
            count=count,
            http_request=http_request,
        ):
            yield json.dumps(result) + "\n"

    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={"X-Total-Questions": str(count)},
    )


@router.get("/api/v1/sql-categories")
async def get_sql_categories():
    """
    Get all supported SQL categories.
    
    Returns:
        Dict with supported categories grouped by generation path
    """
    return get_supported_categories()
