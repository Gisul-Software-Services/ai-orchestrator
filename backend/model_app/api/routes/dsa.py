"""DSA routes for the modular monolith."""

from __future__ import annotations

from fastapi import APIRouter, Body
from starlette.requests import Request

from backend.model_app.schemas.dsa import DSAQuestionRequest
from backend.model_app.services import dsa as dsa_service

router = APIRouter(tags=["dsa"])
dsa_router = router


@router.post("/api/v1/enrich-dsa")
async def enrich_dsa(http_request: Request, problem: dict = Body(...)):
    return await dsa_service.enrich_dsa(http_request, problem)


@router.post("/api/v1/generate-dsa-question")
async def generate_dsa_question(body: DSAQuestionRequest, http_request: Request):
    return await dsa_service.generate_dsa_question(body, http_request)

