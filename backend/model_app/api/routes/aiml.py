"""AIML Competency — API routes (synthetic + library)."""
from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

from backend.model_app.competencies.aiml.schema import AIMLGenerationRequest, AIMLLibraryRequest
from backend.model_app.competencies.aiml import generator as aiml_generator

router = APIRouter(tags=["aiml"])
aiml_router = router


@router.post("/api/v1/generate-aiml")
async def generate_aiml(body: AIMLGenerationRequest, http_request: Request):
    from backend.model_app.services import generation as generation_service
    return await generation_service.generate_aiml(body, http_request)


@router.get("/api/v1/aiml-library/catalog/{catalog_id}/preview")
async def aiml_library_catalog_preview(catalog_id: str):
    return await aiml_generator.aiml_library_catalog_preview(catalog_id)


@router.post("/api/v1/generate-aiml-library")
async def generate_aiml_library(body: AIMLLibraryRequest, http_request: Request):
    return await aiml_generator.generate_aiml_library(body, http_request)
