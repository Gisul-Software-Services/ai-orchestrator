"""Cloud (AWS) Competency — API routes."""
from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from starlette.requests import Request

from backend.model_app.competencies.cloud.schema import CloudQuestionRequest
from backend.model_app.competencies.cloud import generator as cloud_generator

router = APIRouter(tags=["cloud"])
cloud_router = router


@router.post("/api/v1/generate-cloud-question")
async def generate_cloud_question(body: CloudQuestionRequest, http_request: Request):
    """
    Generate AWS Cloud question(s).
    - count=1  : returns a single JSON object
    - count>1  : streams questions as NDJSON (one per line, sent as generated)

    Mode is auto-derived from experience_years (<=5 → code, >5 → scenario)
    or can be explicitly set via the mode field.

    aws_service examples: s3, ec2, lambda, iam, rds, dynamodb, cloudformation
    """
    if not body.aws_service:
        raise HTTPException(status_code=400, detail="aws_service is required (e.g. 's3', 'ec2', 'lambda')")

    count = max(1, min(body.count, 20))
    mode = body.resolved_mode

    if count == 1:
        result = await cloud_generator.generate_cloud_question(
            mode=mode,
            job_role=body.job_role,
            experience_years=body.experience_years,
            difficulty=body.difficulty,
            aws_service=body.aws_service,
            concepts=body.concepts,
            time_limit=body.time_limit,
            http_request=http_request,
        )
        return result

    async def stream_questions():
        async for result in cloud_generator.generate_cloud_questions_bulk(
            mode=mode,
            job_role=body.job_role,
            experience_years=body.experience_years,
            difficulty=body.difficulty,
            aws_service=body.aws_service,
            concepts=body.concepts,
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
