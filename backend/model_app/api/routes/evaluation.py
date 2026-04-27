"""Evaluation routes (DSA + AIML feedback) for the model app."""

from __future__ import annotations

from fastapi import APIRouter, Body, HTTPException
from starlette.requests import Request

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.evaluation.aiml_evaluator import get_aiml_feedback_product_contract
from backend.model_app.evaluation.dsa_evaluator import get_dsa_feedback_product_contract

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

