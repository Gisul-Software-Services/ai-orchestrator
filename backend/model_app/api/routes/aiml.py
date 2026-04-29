"""AIML Competency — API routes."""
from __future__ import annotations

from fastapi import APIRouter
from starlette.requests import Request

from backend.model_app.competencies.aiml.schema import AIMLGenerationRequest, AIMLLibraryRequest
from backend.model_app.competencies.aiml import generator as aiml_generator

router = APIRouter(tags=["aiml"])
aiml_router = router


@router.post("/api/v1/generate-aiml")
async def generate_aiml(body: AIMLGenerationRequest, http_request: Request):
    """
    Generate an AIML assessment question using RAG-matched library dataset.
    Matches from 180-dataset catalog via FAISS semantic search.
    """
    lib_body = AIMLLibraryRequest(
        topic=body.topic,
        difficulty=body.difficulty,
        concepts=body.concepts,
        use_cache=body.use_cache,
        org_id=body.org_id,
    )
    return await aiml_generator.generate_aiml_library(lib_body, http_request)


@router.get("/api/v1/aiml-library/catalog/{catalog_id}/preview")
async def aiml_library_catalog_preview(catalog_id: str):
    """Preview rows from a catalog dataset by ID."""
    return await aiml_generator.aiml_library_catalog_preview(catalog_id)
