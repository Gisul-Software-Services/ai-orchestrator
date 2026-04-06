"""DSA routes are defined on ``backend.model_app.engine.core:app`` (monolith)."""

from __future__ import annotations

from fastapi import APIRouter

dsa_router = APIRouter(prefix="/api/v1", tags=["dsa"])


def attach_dsa_handlers(router: APIRouter) -> None:
    del router
