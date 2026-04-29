"""Evaluation routes (DSA + AIML + SQL feedback) for the model app."""

from __future__ import annotations

import asyncio
import time
import uuid

from fastapi import APIRouter, Body, HTTPException
from starlette.requests import Request

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.evaluation.aiml_evaluator import get_aiml_feedback_product_contract
from backend.model_app.evaluation.dsa_evaluator import get_dsa_feedback_product_contract
from backend.model_app.evaluation.sql_evaluator import get_sql_feedback
from backend.model_app.competencies.sql.eval_schema import SQLEvaluationRequest
from backend.model_app.services.jobs import _job_store_set, _job_store_update

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.post("/dsa")
async def evaluate_dsa(
    http_request: Request,
    payload: dict = Body(...),
):
    bind_usage_meta_from_request(http_request)
    if not payload:
        raise HTTPException(status_code=400, detail="Payload is required")
    return get_dsa_feedback_product_contract(payload=payload, usage_meta=bind_usage_meta_from_request(http_request))


@router.post("/aiml")
async def evaluate_aiml(
    http_request: Request,
    payload: dict = Body(...),
):
    bind_usage_meta_from_request(http_request)
    if not payload:
        raise HTTPException(status_code=400, detail="Payload is required")
    return get_aiml_feedback_product_contract(payload=payload, usage_meta=bind_usage_meta_from_request(http_request))


@router.post("/sql")
async def evaluate_sql(
    http_request: Request,
    payload: SQLEvaluationRequest,
):
    """Synchronous SQL evaluation — returns result directly."""
    usage_meta = bind_usage_meta_from_request(http_request)
    return get_sql_feedback(payload=payload.model_dump(), usage_meta=usage_meta)


@router.post("/sql/async")
async def evaluate_sql_async(
    http_request: Request,
    payload: SQLEvaluationRequest,
):
    """
    Async SQL evaluation — enqueues the LLM call as a background job and
    returns a job_id immediately.  Poll GET /api/v1/job/{job_id} for the result.
    This avoids 429s from the inference engine when multiple evaluations are
    submitted concurrently.
    """
    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        t0 = time.time()
        await _job_store_update(job_id, status="processing")
        try:
            result = await asyncio.to_thread(
                get_sql_feedback, payload=payload_dict, usage_meta=usage_meta
            )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


