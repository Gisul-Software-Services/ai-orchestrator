from __future__ import annotations

from fastapi import FastAPI

from backend.model_app.api.routes.aiml_library import router as aiml_library_router
from backend.model_app.api.routes import system
from backend.model_app.api.routes.catalog import router as catalog_router
from backend.model_app.api.routes.dashboard import router as dashboard_router
from backend.model_app.api.routes.dsa import dsa_router
from backend.model_app.api.routes.generation import generation_router
from backend.model_app.core.app import app
from backend.model_app.middleware.request_log import RequestLogMiddleware

# App composition root: routes live under ``api.routes`` and share the FastAPI
# instance created in ``core.app``.
app.add_middleware(RequestLogMiddleware)
app.include_router(system.router)
app.include_router(generation_router)
app.include_router(dsa_router)
app.include_router(aiml_library_router)
app.include_router(dashboard_router)
app.include_router(catalog_router)

__all__ = ["app", "FastAPI"]
