"""Compatibility wrapper for generation routes."""

from __future__ import annotations

from backend.model_app.api.routes.generation import generation_router


def attach_generation_handlers(router):
    del router

