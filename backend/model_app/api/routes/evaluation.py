"""Evaluation routes (DSA + AIML + SQL + DevOps + Cloud feedback) for the model app."""

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
from backend.model_app.evaluation.devops_evaluator import get_devops_feedback
from backend.model_app.evaluation.cloud_evaluator import get_cloud_feedback
from backend.model_app.evaluation.linux_evaluator import get_linux_feedback
from backend.model_app.evaluation.design_evaluator import get_design_feedback
from backend.model_app.competencies.sql.eval_schema import SQLEvaluationRequest
from backend.model_app.competencies.devops.eval_schema import DevOpsEvalRequest, CloudEvalRequest
from backend.model_app.competencies.design.eval_schema import DesignEvalRequest

# Linux uses the same request shape as DevOps
LinuxEvalRequest = DevOpsEvalRequest
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
    from backend.model_app.core.state import llm_semaphore

    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_sql_feedback, payload=payload_dict, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


@router.post("/devops")
async def evaluate_devops(
    http_request: Request,
    payload: DevOpsEvalRequest,
):
    """DevOps evaluation — scores terminal commands or written answers using Qwen."""
    usage_meta = bind_usage_meta_from_request(http_request)
    return get_devops_feedback(payload=payload.model_dump(), usage_meta=usage_meta)


@router.post("/devops/async")
async def evaluate_devops_async(
    http_request: Request,
    payload: DevOpsEvalRequest,
):
    """Async DevOps evaluation — enqueues LLM call, returns job_id immediately.
    Poll GET /api/v1/job/{job_id} for the result."""
    from backend.model_app.core.state import llm_semaphore

    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_devops_feedback, payload=payload_dict, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


@router.post("/cloud")
async def evaluate_cloud(
    http_request: Request,
    payload: CloudEvalRequest,
):
    """Cloud (AWS) evaluation — delegates to DevOps evaluator with cloud billing route."""
    usage_meta = bind_usage_meta_from_request(http_request)
    return get_cloud_feedback(payload=payload.model_dump(), usage_meta=usage_meta)


@router.post("/cloud/async")
async def evaluate_cloud_async(
    http_request: Request,
    payload: CloudEvalRequest,
):
    """Async Cloud evaluation — enqueues LLM call, returns job_id immediately.
    Poll GET /api/v1/job/{job_id} for the result."""
    from backend.model_app.core.state import llm_semaphore

    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_cloud_feedback, payload=payload_dict, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


@router.post("/dsa/async")
async def evaluate_dsa_async(
    http_request: Request,
    payload: dict = Body(...),
):
    """Async DSA evaluation — enqueues LLM call, returns job_id immediately.
    Poll GET /api/v1/job/{job_id} for the result."""
    from backend.model_app.core.state import llm_semaphore

    if not payload:
        raise HTTPException(status_code=400, detail="Payload is required")
    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_dsa_feedback_product_contract, payload=payload, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}


@router.post("/aiml/async")
async def evaluate_aiml_async(
    http_request: Request,
    payload: dict = Body(...),
):
    """Async AIML evaluation — enqueues LLM call, returns job_id immediately.
    Poll GET /api/v1/job/{job_id} for the result."""
    from backend.model_app.core.state import llm_semaphore

    if not payload:
        raise HTTPException(status_code=400, detail="Payload is required")
    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_aiml_feedback_product_contract, payload=payload, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}




@router.post("/linux")
async def evaluate_linux(
    http_request: Request,
    payload: LinuxEvalRequest,
):
    """Linux/Shell evaluation — scores terminal commands or written answers using Qwen."""
    usage_meta = bind_usage_meta_from_request(http_request)
    return get_linux_feedback(payload=payload.model_dump(), usage_meta=usage_meta)


@router.post("/linux/async")
async def evaluate_linux_async(
    http_request: Request,
    payload: LinuxEvalRequest,
):
    """Async Linux/Shell evaluation — enqueues LLM call, returns job_id immediately.
    Poll GET /api/v1/job/{job_id} for the result."""
    from backend.model_app.core.state import llm_semaphore

    usage_meta = bind_usage_meta_from_request(http_request)
    job_id = str(uuid.uuid4())
    payload_dict = payload.model_dump()

    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _run():
        await _job_store_update(job_id, status="processing")
        try:
            async with llm_semaphore:
                result = await asyncio.to_thread(
                    get_linux_feedback, payload=payload_dict, usage_meta=usage_meta
                )
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
        except Exception as exc:
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(exc)})

    asyncio.create_task(_run())
    return {"job_id": job_id, "status": "pending"}
