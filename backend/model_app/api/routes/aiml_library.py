"""AIML library routes for the modular monolith."""

from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

from backend.model_app.schemas.aiml import AIMLLibraryRequest
from backend.model_app.services import aiml as aiml_service

router = APIRouter(tags=["aiml-library"])


@router.get("/api/v1/aiml-library/catalog/{catalog_id}/preview")
async def aiml_library_catalog_preview(catalog_id: str):
    return await aiml_service.aiml_library_catalog_preview(catalog_id)


@router.post("/api/v1/generate-aiml-library")
async def generate_aiml_library(body: AIMLLibraryRequest, http_request: Request):
    return await aiml_service.generate_aiml_library(body, http_request)
