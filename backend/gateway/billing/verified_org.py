"""
When REQUIRE_VERIFIED_ORG_FOR_GENERATION=true, blocks unverified requests
on POST generation paths and GET catalog preview.

Never blocks: /health, /stats, /docs, /billing/*, /api/v1/metrics/*,
GET /api/v1/job/*, POST /api/v1/clear-cache

Returns 401 if X-Org-Id header is missing entirely.
Returns 403 if org header present but org_verified=False (not in organization_db).
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from backend.gateway.core.settings import get_settings

logger = logging.getLogger(__name__)

GENERATION_POST_PATHS = frozenset(
    {
        "/api/v1/generate-topics",
        "/api/v1/generate-mcq",
        "/api/v1/generate-subjective",
        "/api/v1/generate-coding",
        "/api/v1/generate-sql",
        "/api/v1/generate-aiml",
        "/api/v1/generate-aiml-library",
        "/api/v1/generate-dsa-question",
        "/api/v1/enrich-dsa",
    }
)

PREVIEW_GET_PREFIX = "/api/v1/aiml-library/catalog/"


class VerifiedOrgRequiredMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not get_settings().require_verified_org_for_generation:
            return await call_next(request)

        path = request.url.path
        method = request.method

        needs_check = (method == "POST" and path in GENERATION_POST_PATHS) or (
            method == "GET" and path.startswith(PREVIEW_GET_PREFIX) and path.endswith("/preview")
        )

        if not needs_check:
            return await call_next(request)

        # Admin/server-to-server requests may authenticate with X-Api-Key only.
        # In that case, defer verification to gateway.main where API key is
        # resolved to org_id and validated against Mongo.
        api_key = request.headers.get("X-Api-Key", "").strip()
        if api_key:
            return await call_next(request)

        org_id = request.headers.get("X-Org-Id", "").strip()
        org_verified = getattr(request.state, "org_verified", False)

        if not org_id:
            return JSONResponse(
                status_code=401,
                content={
                    "error": "ORG_HEADER_MISSING",
                    "detail": "X-Org-Id header is required for generation endpoints.",
                },
            )

        if not org_verified:
            logger.info(
                "rejected generation: unknown org header=%r path=%s", org_id, path
            )
            return JSONResponse(
                status_code=403,
                content={
                    "error": "ORG_NOT_VERIFIED",
                    "detail": f"Organisation '{org_id}' is not registered in the platform.",
                },
            )

        return await call_next(request)
