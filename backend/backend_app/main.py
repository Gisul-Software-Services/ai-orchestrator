"""
Production FastAPI entrypoint.

Run from ``backend/``::

    PYTHONPATH=. uvicorn backend_app.main:app --host 0.0.0.0 --port 9000
"""

from __future__ import annotations

import logging

from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.requests import Request

from backend_app.api.routers import system
from backend_app.api.routers.catalog import router as catalog_router
from backend_app.api.routers.dashboard import router as dashboard_router
from backend_app.api.routers.dsa import dsa_router
from backend_app.api.routers.generation import generation_router
from backend_app.billing.org_context import OrgContextMiddleware
from backend_app.billing.verified_org import VerifiedOrgRequiredMiddleware
from backend_app.billing.router import router as billing_router
from backend_app.core.settings import get_settings
from backend_app.engine.core import app
from backend_app.middleware.request_log import RequestLogMiddleware

logger = logging.getLogger(__name__)

_s = get_settings()


def _cors_is_wide_open(origins: list[str]) -> bool:
    return not origins or origins == ["*"] or (len(origins) == 1 and origins[0] == "*")


@app.on_event("startup")
async def _production_startup_checks() -> None:
    """Log once when ENVIRONMENT=production — does not alter request handling."""
    # Always log effective org-gating config for debugging.
    # This helps confirm the correct `.env` file was loaded when running uvicorn locally.
    logger.info(
        "Effective config: REQUIRE_VERIFIED_ORG_FOR_GENERATION=%s ENVIRONMENT=%s organization_db=%s billing_db=%s",
        _s.require_verified_org_for_generation,
        _s.environment,
        _s.organization_db_name,
        _s.billing_db_name,
    )
    if _s.environment != "production":
        return
    if _cors_is_wide_open(_s.allowed_origins):
        logger.warning(
            "ENVIRONMENT=production but ALLOWED_ORIGINS is open (*). "
            "Set ALLOWED_ORIGINS to explicit UI origins (e.g. https://app.example.com)."
        )
    if not _s.require_verified_org_for_generation:
        logger.warning(
            "ENVIRONMENT=production but REQUIRE_VERIFIED_ORG_FOR_GENERATION=false — "
            "generation and catalog preview are not org-gated."
        )


app.add_middleware(
    CORSMiddleware,
    allow_origins=_s.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(VerifiedOrgRequiredMiddleware)
app.add_middleware(OrgContextMiddleware)
app.add_middleware(RequestLogMiddleware)


@app.exception_handler(RequestValidationError)
async def _validation_error_handler(request: Request, exc: RequestValidationError):
    # Structured errors (no raw str(exc) — avoids leaking internal repr in production logs/clients)
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "detail": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def _global_error_handler(request, exc):
    if isinstance(exc, StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"},
    )


app.include_router(system.router)
app.include_router(generation_router)
app.include_router(dsa_router)
app.include_router(dashboard_router)
app.include_router(catalog_router)
app.include_router(billing_router)
