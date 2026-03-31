"""
Reads ``X-Org-Id`` from the request header, validates against Aaptor's
``organization_db.organizations``, and stamps ``request.state.org_id`` for metering.

Missing header, unknown org, or Mongo failures → ``unattributed``; never blocks generation.
"""

from __future__ import annotations

import logging
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend_app.billing.db import get_client
from backend_app.core.settings import get_settings

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
            s = get_settings()
            client = get_client()
            # Prefer dedicated org DB first; fallback to billing DB for legacy setups.
            # Keep deterministic order and do not abort lookup if one DB/collection
            # has permissions/index issues.
            db_names = [s.organization_db_name]
            if s.billing_db_name != s.organization_db_name:
                db_names.append(s.billing_db_name)
            # Be tolerant to legacy variants: collection name and key casing differ
            # across environments (organizations vs organization, orgId vs orgID/org_id).
            collections = ("organizations", "organization")
            filters = (
                {"orgId": org_id},
                {"orgID": org_id},
                {"org_id": org_id},
                {"orgId": {"$regex": f"^{re.escape(org_id)}$", "$options": "i"}},
                {"orgID": {"$regex": f"^{re.escape(org_id)}$", "$options": "i"}},
                {"org_id": {"$regex": f"^{re.escape(org_id)}$", "$options": "i"}},
            )
            org_doc = None
            for db_name in db_names:
                db = client[db_name]
                for col in collections:
                    coll = db[col]
                    for q in filters:
                        try:
                            org_doc = await coll.find_one(
                                q,
                                projection={
                                    "orgId": 1,
                                    "orgID": 1,
                                    "org_id": 1,
                                    "name": 1,
                                },
                            )
                        except Exception as qe:
                            logger.warning(
                                "org lookup candidate failed: db=%s col=%s query=%s err=%s",
                                db_name,
                                col,
                                q,
                                qe,
                            )
                            org_doc = None
                        if org_doc:
                            break
                    if org_doc:
                        break
                if org_doc:
                    break
        except Exception as e:
            logger.warning("org lookup failed: %s", e)
            org_doc = None

        if org_doc:
            resolved_org_id = (
                org_doc.get("orgId") or org_doc.get("orgID") or org_doc.get("org_id")
            )
            request.state.org_id = resolved_org_id or "unattributed"
            request.state.org_name = org_doc.get("name") or ""
            request.state.org_verified = True
        else:
            # Helps diagnose cases where org exists in Mongo but lookup still fails
            # (e.g. env points at a different cluster/db, or stale service running).
            try:
                # Count matches per candidate DB/collection/field variant.
                # This turns the "unknown org" confusion into a concrete mismatch report.
                logger.info(
                    "org lookup miss: header=%r dbs=%r collections=%r",
                    org_id,
                    [get_settings().organization_db_name, get_settings().billing_db_name],
                    ["organizations", "organization"],
                )

                s = get_settings()
                client = get_client()
                db_names = [s.organization_db_name]
                if s.billing_db_name != s.organization_db_name:
                    db_names.append(s.billing_db_name)
                # Match possible accidental whitespace around stored IDs.
                trimmed = org_id.strip()
                esc = re.escape(trimmed)
                regex_trim = {"$regex": f"^\\s*{esc}\\s*$", "$options": "i"}

                for db_name in db_names:
                    db = client[db_name]
                    for col in ("organizations", "organization"):
                        coll = db[col]
                        try:
                            total = await coll.count_documents({})
                        except Exception:
                            total = -1
                        for field in ("orgId", "orgID", "org_id"):
                            c = await coll.count_documents({field: regex_trim})
                            exists_count = await coll.count_documents({field: {"$exists": True}})
                            logger.info(
                                "org lookup candidates: db=%s col=%s total=%s field=%s exists=%s matches=%s for %r",
                                db_name,
                                col,
                                total,
                                field,
                                exists_count,
                                c,
                                org_id,
                            )
            except Exception:
                pass
            request.state.org_id = "unattributed"
            request.state.org_name = ""
            request.state.org_verified = False

        return await call_next(request)
