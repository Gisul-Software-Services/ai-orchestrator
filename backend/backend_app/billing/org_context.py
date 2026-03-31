"""
Reads ``X-Org-Id`` from the request header, validates against Aaptor's
``organization_db.organizations``, and stamps ``request.state.org_id`` for metering.

Missing header, unknown org, or Mongo failures → ``unattributed``; never blocks generation.
"""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend_app.billing.db import aaptor_orgs

logger = logging.getLogger(__name__)

SKIP_PATHS = frozenset(
    {
        "/",
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/stats",
        "/api/v1/stats",
    }
)
_SKIP_PREFIXES = ("/billing/",)


class OrgContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path
        if path in SKIP_PATHS or any(path.startswith(p) for p in _SKIP_PREFIXES):
            return await call_next(request)

        org_id = (request.headers.get("X-Org-Id") or "").strip()

        if not org_id:
            request.state.org_id = "unattributed"
            request.state.org_name = ""
            request.state.org_verified = False
            return await call_next(request)

        try:
            org_doc = await aaptor_orgs().find_one(
                {"orgId": org_id},
                projection={"orgId": 1, "name": 1},
            )
        except Exception as e:
            logger.warning("org lookup failed: %s", e)
            org_doc = None

        if org_doc:
            request.state.org_id = org_doc.get("orgId", "unattributed")
            request.state.org_name = org_doc.get("name") or ""
            request.state.org_verified = True
        else:
            request.state.org_id = "unattributed"
            request.state.org_name = ""
            request.state.org_verified = False

        return await call_next(request)
