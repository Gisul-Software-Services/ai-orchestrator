from __future__ import annotations

from fastapi import FastAPI

from backend.model_app.api.routers import system
from backend.model_app.api.routers.catalog import router as catalog_router
from backend.model_app.api.routers.dashboard import router as dashboard_router
from backend.model_app.api.routers.dsa import dsa_router
from backend.model_app.api.routers.generation import generation_router
from backend.model_app.engine.core import app
from backend.model_app.middleware.request_log import RequestLogMiddleware

# engine.core owns generation/system internals; this file wires compatibility routers.
app.add_middleware(RequestLogMiddleware)
app.include_router(system.router)
app.include_router(generation_router)
app.include_router(dsa_router)
app.include_router(dashboard_router)
app.include_router(catalog_router)

__all__ = ["app", "FastAPI"]
