"""
Optional extra routers (generation/DSA) — the monolith in ``backend_app.engine.core``
already registers all HTTP routes on ``app``. This module is a no-op placeholder.
"""

from __future__ import annotations

from fastapi import FastAPI


def register_all_api_routers(app: FastAPI) -> None:
    """Legacy hook — no duplicate registration when using ``engine.core`` monolith."""
    del app  # unused
