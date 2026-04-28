"""SQL question generation route."""
from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from backend.model_app.competencies.sql.schema import SQLQuestionRequest
from backend.model_app.competencies.sql import generator as sql_generator

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
