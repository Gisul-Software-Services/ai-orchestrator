"""Generation routes for the modular monolith."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

from backend.model_app.schemas.aiml import AIMLGenerationRequest
from backend.model_app.schemas.generation import (
    CodingGenerationRequest,
    MCQGenerationRequest,
    SQLGenerationRequest,
    SubjectiveGenerationRequest,
    TopicGenerationRequest,
)
from backend.model_app.services import generation as generation_service

router = APIRouter(tags=["generation"])
generation_router = router


@router.post("/api/v1/generate-topics")
async def generate_topics(body: TopicGenerationRequest, http_request: Request):
    return await generation_service.generate_topics(body, http_request)


@router.post("/api/v1/generate-mcq")
async def generate_mcq(body: MCQGenerationRequest, http_request: Request):
    return await generation_service.generate_mcq(body, http_request)


@router.post("/api/v1/generate-subjective")
async def generate_subjective(body: SubjectiveGenerationRequest, http_request: Request):
    return await generation_service.generate_subjective(body, http_request)


@router.post("/api/v1/generate-coding")
async def generate_coding(body: CodingGenerationRequest, http_request: Request):
    return await generation_service.generate_coding(body, http_request)


@router.post("/api/v1/generate-sql")
async def generate_sql(body: SQLGenerationRequest, http_request: Request):
    return await generation_service.generate_sql(body, http_request)


@router.post("/api/v1/generate-aiml")
async def generate_aiml(body: AIMLGenerationRequest, http_request: Request):
    return await generation_service.generate_aiml(body, http_request)

