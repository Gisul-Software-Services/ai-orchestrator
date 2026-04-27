"""DSA routes for the modular monolith."""

from __future__ import annotations

import json

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from backend.model_app.competencies.dsa.schema import DSAQuestionRequest
from backend.model_app.services import dsa as dsa_service
from backend.model_app.competencies.dsa import generator as dsa_generator

router = APIRouter(tags=["dsa"])
dsa_router = router


@router.post("/api/v1/enrich-dsa")
async def enrich_dsa(http_request: Request, problem: dict = Body(...)):
    return await dsa_service.enrich_dsa(http_request, problem)


@router.post("/api/v1/generate-dsa-question")
async def generate_dsa_question(body: DSAQuestionRequest, http_request: Request):
    """
    Generate DSA question(s) using bulk RAG retrieval + Qwen reword.
    - count=1 : returns a single JSON object
    - count>1 : streams questions as NDJSON (one per line, sent as generated)
    """
    if not body.languages:
        raise HTTPException(status_code=400, detail="At least one language must be selected")

    count = max(1, min(body.count, 20))

    if count == 1:
        result = await dsa_generator.generate_dsa_question(
            difficulty=body.difficulty,
            topic=body.topic,
            concepts=body.concepts,
            languages=body.languages,
            http_request=http_request,
        )
        return result

    # Bulk — stream questions as NDJSON
    async def stream_questions():
        async for result in dsa_generator.generate_dsa_questions_bulk(
            difficulty=body.difficulty,
            topic=body.topic,
            concepts=body.concepts,
            languages=body.languages,
            count=count,
            http_request=http_request,
        ):
            yield json.dumps(result) + "\n"

    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={"X-Total-Questions": str(count)},
    )
