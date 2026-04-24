"""Evaluation routes (DSA + AIML feedback) for the model app.

These routes are primarily for internal/testing use.
"""

from __future__ import annotations

from fastapi import APIRouter, Body
from starlette.requests import Request

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.evaluation.aiml_evaluator import get_aiml_feedback_product_contract
from backend.model_app.evaluation.dsa_evaluator import get_dsa_feedback_product_contract
from backend.model_app.services import aiml as aiml_service

router = APIRouter(prefix="/api/v1/evaluation", tags=["evaluation"])


@router.post("/dsa")
async def evaluate_dsa(
    http_request: Request,
    payload: dict = Body(...),
):
    usage_meta = bind_usage_meta_from_request(http_request)
    # Accept both:
    # - legacy internal payload (code/problem_id/etc.)
    # - Aaptor feedback_kwargs payload (source_code/question_title/etc.)
    if "source_code" in payload or "question_title" in payload:
        return get_dsa_feedback_product_contract(payload=payload, usage_meta=usage_meta)
    # legacy path: keep existing response for internal testing
    from backend.model_app.services import dsa as dsa_service

    return dsa_service.evaluate_dsa_submission(
        http_request=http_request,
        code=str(payload.get("code") or ""),
        language=str(payload.get("language") or "python"),
        problem_title=str(payload.get("problem_title") or ""),
        problem_id=str(payload.get("problem_id") or ""),
        test_results=payload.get("test_results") or {},
        score=int(payload.get("score") or 0),
    )


@router.post("/aiml")
async def evaluate_aiml(
    http_request: Request,
    payload: dict = Body(...),
):
    usage_meta = bind_usage_meta_from_request(http_request)
    # Aaptor EvaluateSubmissionRequest path (source_code + outputs + tasks/test_cases).
    if "source_code" in payload and ("outputs" in payload or "test_cases" in payload or "tasks" in payload):
        return get_aiml_feedback_product_contract(payload=payload, usage_meta=usage_meta)

    # Legacy internal path (keep existing for compatibility)
    expected_output = payload.get("expected_output")
    actual_output = payload.get("actual_output")
    return aiml_service.evaluate_aiml_submission(
        http_request=http_request,
        code=str(payload.get("code") or ""),
        language=str(payload.get("language") or "python"),
        task_title=str(payload.get("task_title") or ""),
        task_id=str(payload.get("task_id") or ""),
        expected_output=expected_output if isinstance(expected_output, dict) or expected_output is None else {"value": expected_output},
        actual_output=actual_output if isinstance(actual_output, dict) or actual_output is None else {"value": actual_output},
    )

