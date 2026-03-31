"""
System-style routes (``/``, ``/health``, ``/stats``, job polling) are registered on
``backend_app.engine.core.app`` in the monolith. This module is a compatibility stub so
imports do not fail; do not ``include_router`` here if those paths already exist on ``app``.
"""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["system-compat"])
