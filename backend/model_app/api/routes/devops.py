"""DevOps / Cloud Competency — API routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from backend.model_app.competencies.devops.schema import DevOpsQuestionRequest
from backend.model_app.competencies.devops import generator as devops_generator

router = APIRouter(tags=["devops"])
devops_router = router


@router.post("/api/v1/generate-devops-question")
async def generate_devops_question(body: DevOpsQuestionRequest, http_request: Request):
    """
    Generate DevOps/Cloud question(s).
    - count=1  : returns a single JSON object
    - count>1  : streams questions as NDJSON (one per line, sent as generated)

    Mode is auto-derived from experience_years (<=5 → code, >5 → scenario)
    or can be explicitly set via the mode field.
    """
    if not body.focus_area:
        raise HTTPException(status_code=400, detail="focus_area is required")

    count = max(1, min(body.count, 20))
    mode = body.resolved_mode

    if count == 1:
        result = await devops_generator.generate_devops_question(
            mode=mode,
            job_role=body.job_role,
            experience_years=body.experience_years,
            difficulty=body.difficulty,
            focus_area=body.focus_area,
            topics=body.topics,
            time_limit=body.time_limit,
            http_request=http_request,
        )
        return result

    async def stream_questions():
        async for result in devops_generator.generate_devops_questions_bulk(
            mode=mode,
            job_role=body.job_role,
            experience_years=body.experience_years,
            difficulty=body.difficulty,
            focus_area=body.focus_area,
            topics=body.topics,
            time_limit=body.time_limit,
            count=count,
            http_request=http_request,
        ):
            yield json.dumps(result) + "\n"

    return StreamingResponse(
        stream_questions(),
        media_type="application/x-ndjson",
        headers={"X-Total-Questions": str(count)},
    )
