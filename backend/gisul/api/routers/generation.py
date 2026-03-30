"""
Generation routes are defined on ``gisul.engine.core:app`` (monolith).

Kept so imports like ``gisul.api.routers.generation.generation_router`` do not break.
"""

from __future__ import annotations

from fastapi import APIRouter

generation_router = APIRouter(prefix="/api/v1", tags=["generation"])


def attach_generation_handlers(router: APIRouter) -> None:
    """No-op — handlers live on the monolith app."""
    del router
