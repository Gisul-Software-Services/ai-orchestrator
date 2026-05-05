"""SQL question generation route."""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from backend.model_app.competencies.sql.schema import SQLQuestionRequest
from backend.model_app.competencies.sql import generator as sql_generator
from backend.model_app.competencies.sql import schema_generator

router = APIRouter(tags=["sql"])
sql_router = router


@router.post("/api/v1/generate-sql-question")
async def generate_sql_question(body: SQLQuestionRequest, http_request: Request):
    """
    Generate SQL question(s) using bulk RAG retrieval + Qwen reword.
    - count=1 : returns a single JSON object
    - count>1 : streams questions as NDJSON (one per line, sent as generated)
    """
    count = max(1, min(body.count, 20))

    if count == 1:
        return await sql_generator.generate_sql_question(
            difficulty=body.difficulty,
            topic=body.topic,
            sql_category=body.sql_category,
            http_request=http_request,
        )

    async def stream_questions():
        async for result in sql_generator.generate_sql_questions_bulk(
            difficulty=body.difficulty,
            topic=body.topic,
            sql_category=body.sql_category,
            count=count,
            http_request=http_request,
        ):
            yield json.dumps(result) + "\n"

    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={"X-Total-Questions": str(count)},
    )


@router.post("/api/v1/generate-sql-question-from-schema")
async def generate_sql_question_from_schema(body: SQLQuestionRequest, http_request: Request):
    """
    Generate SQL question(s) dynamically from database schemas stored in MongoDB.
    
    This endpoint generates unique SQL questions by:
    1. Selecting an appropriate schema from MongoDB based on difficulty, category, and domain
    2. Using LLM to generate a contextually relevant question
    3. Validating the generated query
    
    - count=1 : returns a single JSON object
    - count>1 : streams questions as NDJSON (one per line, sent as generated)
    
    Benefits:
    - Unlimited question variety (never repeats exactly)
    - Real-world database schemas
    - Domain-specific contexts
    """
    count = max(1, min(body.count, 20))

    if count == 1:
        return await schema_generator.generate_question_from_schema(
            difficulty=body.difficulty,
            sql_category=body.sql_category or body.topic,
            domain=None,  # TODO: Add domain parameter to SQLQuestionRequest
            http_request=http_request,
        )

    async def stream_questions():
        async for result in schema_generator.generate_sql_questions_from_schema_bulk(
            difficulty=body.difficulty,
            sql_category=body.sql_category or body.topic,
            domain=None,  # TODO: Add domain parameter to SQLQuestionRequest
            count=count,
            http_request=http_request,
        ):
            yield json.dumps(result) + "\n"

    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={"X-Total-Questions": str(count)},
    )
