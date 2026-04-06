from __future__ import annotations

import asyncio
import hashlib
import logging
import re
import time
import uuid
from typing import Iterable

import httpx
import redis.asyncio as redis_asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pymongo import MongoClient

from backend.gateway.billing.org_context import OrgContextMiddleware
from backend.gateway.billing.metering import get_usage_meta_header_value
from backend.gateway.billing.router import router as billing_router
from backend.gateway.billing.verified_org import VerifiedOrgRequiredMiddleware
from backend.gateway.core.settings import get_settings
from backend.gateway.middleware.request_log import RequestLogMiddleware

app = FastAPI(title="Gisul Gateway")
logger = logging.getLogger(__name__)

_PROXY_TIMEOUT = httpx.Timeout(connect=5.0, read=180.0, write=10.0, pool=5.0)

_ORG_GATED_POST_PATHS = frozenset(
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
_mongo_client: MongoClient | None = None
_redis_client: redis_asyncio.Redis | None = None

s = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=s.allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(VerifiedOrgRequiredMiddleware)
app.add_middleware(OrgContextMiddleware)
app.add_middleware(RequestLogMiddleware)
app.include_router(billing_router)


def _model_service_url() -> str:
    return get_settings().model_service_url.rstrip("/")


def _require_verified_org_for_generation() -> bool:
    return bool(get_settings().require_verified_org_for_generation)


def _mongodb_uri() -> str:
    return (get_settings().mongodb_uri or "").strip()


def _organization_db_name() -> str:
    return get_settings().organization_db_name


def _billing_db_name() -> str:
    return get_settings().billing_db_name


def _get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(_mongodb_uri())
    return _mongo_client


def _get_redis_client() -> redis_asyncio.Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = redis_asyncio.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


def _validate_api_key_sync(raw_key: str) -> tuple[bool, str]:
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    coll = _get_mongo_client()[_billing_db_name()]["api_keys"]
    doc = coll.find_one({"key_hash": key_hash, "status": "active"}, projection={"org_id": 1})
    if doc:
        oid = (doc.get("org_id") or "").strip()
        return True, oid
    return False, ""


async def _check_rate_limit(org_id: str) -> bool:
    if not org_id:
        return True
    try:
        window = int(time.time() // 60)
        key = f"ratelimit:{org_id.strip()}:{window}"
        r = _get_redis_client()
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, 120)
        return count <= int(get_settings().rate_limit_per_org)
    except Exception:
        return True


def _org_exists_sync(org_id: str) -> bool:
    client = _get_mongo_client()
    db_names = [_organization_db_name()]
    if _billing_db_name() != _organization_db_name():
        db_names.append(_billing_db_name())
    collections = ("organizations", "organization")
    esc = re.escape(org_id.strip())
    regex_trim = {"$regex": f"^\\s*{esc}\\s*$", "$options": "i"}
    for db_name in db_names:
        db = client[db_name]
        for col in collections:
            coll = db[col]
            for field in ("orgId", "orgID", "org_id"):
                if coll.find_one({field: regex_trim}, projection={"_id": 1}):
                    return True
    return False


async def _verify_org_header_or_block(request: Request, target_path: str) -> Response | None:
    if not _require_verified_org_for_generation():
        return None
    if request.method != "POST" or target_path not in _ORG_GATED_POST_PATHS:
        return None

    api_key = (request.headers.get("X-Api-Key") or "").strip()
    org_id = ""

    if api_key:
        if not _mongodb_uri():
            return JSONResponse(
                status_code=503,
                content={"error": "ORG_VERIFICATION_UNAVAILABLE", "detail": "MONGODB_URI is not configured in gateway."},
            )
        try:
            ok, org_from_key = await asyncio.to_thread(_validate_api_key_sync, api_key)
        except Exception:
            ok, org_from_key = False, ""
        if not ok:
            return JSONResponse(status_code=401, content={"error": "INVALID_API_KEY", "detail": "Invalid or inactive API key."})
        org_id = (org_from_key or "").strip()
        if not org_id:
            return JSONResponse(status_code=401, content={"error": "INVALID_API_KEY", "detail": "API key has no org_id."})
    else:
        org_id = (request.headers.get("X-Org-Id") or "").strip()
        if not org_id:
            return JSONResponse(
                status_code=401,
                content={"error": "ORG_HEADER_MISSING", "detail": "X-Org-Id header is required for generation endpoints."},
            )

    if not _mongodb_uri():
        return JSONResponse(
            status_code=503,
            content={"error": "ORG_VERIFICATION_UNAVAILABLE", "detail": "MONGODB_URI is not configured in gateway."},
        )

    try:
        verified = await asyncio.to_thread(_org_exists_sync, org_id)
    except Exception:
        verified = False

    if verified:
        request.state.verified_org_id = org_id
        return None

    return JSONResponse(
        status_code=403,
        content={"error": "ORG_NOT_VERIFIED", "detail": f"Organisation '{org_id}' is not registered in the platform."},
    )


def _filtered_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    hop_by_hop = {"host", "connection", "content-length", "accept-encoding"}
    out: dict[str, str] = {}
    for k, v in headers:
        if k.lower() in hop_by_hop:
            continue
        out[k] = v
    return out


def _normalize_target_path(target_path: str) -> str:
    target_path = target_path.replace("/api/v1/api/v1/", "/api/v1/", 1).replace("/api/v1/api/v1", "/api/v1", 1)
    target_path = target_path.replace("/api/v1/billing/v1/", "/billing/v1/", 1).replace("/api/v1/billing/v1", "/billing/v1", 1)
    return target_path


async def _proxy(request: Request, target_path: str) -> Response:
    url = f"{_model_service_url()}{target_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _filtered_headers(request.headers.items())
    request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
    headers["x-request-id"] = request_id
    headers["x-usage-meta"] = get_usage_meta_header_value(request)
    verified_org = getattr(request.state, "verified_org_id", None)
    if verified_org:
        headers = dict(headers)
        headers["X-Org-Id"] = str(verified_org).strip()
    body = await request.body()

    async with httpx.AsyncClient(timeout=_PROXY_TIMEOUT) as client:
        try:
            resp = await client.request(method=request.method, url=url, headers=headers, content=body if body else None)
        except httpx.HTTPError:
            return JSONResponse(
                status_code=502,
                content={
                    "error": "UPSTREAM_UNREACHABLE",
                    "detail": f"Model service is unreachable at '{_model_service_url()}'.",
                },
            )

    resp_headers: dict[str, str] = {}
    for k, v in resp.headers.items():
        if k.lower() in ("content-length", "transfer-encoding", "connection"):
            continue
        resp_headers[k] = v
    resp_headers["x-request-id"] = request_id

    return Response(content=resp.content, status_code=resp.status_code, headers=resp_headers)


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def catch_all(request: Request, full_path: str) -> Response:
    target_path = _normalize_target_path(f"/{full_path}")
    blocked = await _verify_org_header_or_block(request, target_path)
    if blocked is not None:
        return blocked

    if _require_verified_org_for_generation() and request.method == "POST" and target_path in _ORG_GATED_POST_PATHS:
        org_for_rl = (getattr(request.state, "verified_org_id", None) or "").strip()
        if org_for_rl and not await _check_rate_limit(org_for_rl):
            return JSONResponse(
                status_code=429,
                content={
                    "error": "RATE_LIMIT_EXCEEDED",
                    "detail": f"Org {org_for_rl} exceeded {get_settings().rate_limit_per_org} requests/minute",
                },
                headers={"Retry-After": "60"},
            )

    return await _proxy(request, target_path)
