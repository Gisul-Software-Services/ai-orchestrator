"""Compatibility wrapper for DSA routes."""

from __future__ import annotations

from backend.model_app.api.routes.dsa import dsa_router


def attach_dsa_handlers(router):
    del router

