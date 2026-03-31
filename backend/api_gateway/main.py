from __future__ import annotations

import asyncio
import logging
import os
import re
from typing import Iterable

import httpx
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from pymongo import MongoClient

app = FastAPI(title="Gisul Backend API (Lightweight)")
logger = logging.getLogger(__name__)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

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


def _model_service_url() -> str:
    # Points to the model service base URL (scheme + host + port), no trailing slash.
    return os.environ.get("MODEL_SERVICE_URL", "http://model-service:7001").rstrip("/")


def _require_verified_org_for_generation() -> bool:
    return os.environ.get("REQUIRE_VERIFIED_ORG_FOR_GENERATION", "true").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _mongodb_uri() -> str:
    return os.environ.get("MONGODB_URI", "").strip()


def _organization_db_name() -> str:
    return os.environ.get("ORGANIZATION_DB_NAME", "organization_db").strip() or "organization_db"


def _billing_db_name() -> str:
    return os.environ.get("BILLING_DB_NAME", "aaptor_model").strip() or "aaptor_model"


def _get_mongo_client() -> MongoClient:
    global _mongo_client
    if _mongo_client is None:
        _mongo_client = MongoClient(_mongodb_uri())
    return _mongo_client


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

    org_id = (request.headers.get("X-Org-Id") or "").strip()
    if not org_id:
        logger.info(
            "org verification failed: missing X-Org-Id method=%s path=%s",
            request.method,
            target_path,
        )
        return JSONResponse(
            status_code=401,
            content={
                "error": "ORG_HEADER_MISSING",
                "detail": "X-Org-Id header is required for generation endpoints.",
            },
        )

    if not _mongodb_uri():
        logger.warning(
            "org verification unavailable: MONGODB_URI missing method=%s path=%s org=%r",
            request.method,
            target_path,
            org_id,
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "ORG_VERIFICATION_UNAVAILABLE",
                "detail": "MONGODB_URI is not configured in api-gateway.",
            },
        )
    try:
        verified = await asyncio.to_thread(_org_exists_sync, org_id)
    except Exception:
        logger.warning(
            "org verification mongo check failed; trying fallback method=%s path=%s org=%r",
            request.method,
            target_path,
            org_id,
        )
        # Fallback: if direct Mongo verification is temporarily unavailable in gateway
        # runtime, use model-service profile lookup so requests are still policy-gated.
        profile_url = f"{_model_service_url()}/billing/v1/orgs/{org_id}/profile"
        async with httpx.AsyncClient(timeout=httpx.Timeout(8.0)) as client:
            try:
                resp = await client.get(profile_url)
            except Exception:
                logger.warning(
                    "org verification failed: fallback unavailable method=%s path=%s org=%r",
                    request.method,
                    target_path,
                    org_id,
                )
                return JSONResponse(
                    status_code=503,
                    content={
                        "error": "ORG_VERIFICATION_UNAVAILABLE",
                        "detail": "Unable to verify organization at this time.",
                    },
                )
        if resp.status_code == 200:
            logger.info(
                "org verification passed (fallback) method=%s path=%s org=%r",
                request.method,
                target_path,
                org_id,
            )
            return None
        logger.info(
            "org verification failed (fallback): method=%s path=%s org=%r status=%s",
            request.method,
            target_path,
            org_id,
            resp.status_code,
        )
        return JSONResponse(
            status_code=403,
            content={
                "error": "ORG_NOT_VERIFIED",
                "detail": f"Organisation '{org_id}' is not registered in the platform.",
            },
        )
    if verified:
        logger.info(
            "org verification passed method=%s path=%s org=%r",
            request.method,
            target_path,
            org_id,
        )
        return None
    logger.info(
        "org verification failed method=%s path=%s org=%r",
        request.method,
        target_path,
        org_id,
    )
    return JSONResponse(
        status_code=403,
        content={
            "error": "ORG_NOT_VERIFIED",
            "detail": f"Organisation '{org_id}' is not registered in the platform.",
        },
    )


def _filtered_headers(headers: Iterable[tuple[str, str]]) -> dict[str, str]:
    hop_by_hop = {
        "host",
        "connection",
        "content-length",
        "accept-encoding",
    }
    out: dict[str, str] = {}
    for k, v in headers:
        lk = k.lower()
        if lk in hop_by_hop:
            continue
        # Avoid forwarding hop-by-hop and keep client context for org metering.
        out[k] = v
    return out


def _normalize_target_path(target_path: str) -> str:
    """
    Be tolerant to accidental double-prefixing from misconfigured clients.

    Example:
      /api/v1/api/v1/generate-aiml-library -> /api/v1/generate-aiml-library
    """
    # Collapse only the first duplicated occurrence.
    target_path = target_path.replace(
        "/api/v1/api/v1/", "/api/v1/", 1
    ).replace("/api/v1/api/v1", "/api/v1", 1)

    # Some deployments route billing admin endpoints as `/api/v1/billing/v1/...`
    # even though the backend billing router is mounted at `/billing/v1`.
    # Normalize this so the backend sees the canonical `/billing/v1/...` path.
    target_path = target_path.replace(
        "/api/v1/billing/v1/", "/billing/v1/", 1
    ).replace("/api/v1/billing/v1", "/billing/v1", 1)
    return target_path


async def _proxy(request: Request, target_path: str) -> Response:
    url = f"{_model_service_url()}{target_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _filtered_headers(request.headers.items())
    body = await request.body()

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        try:
            resp = await client.request(
                method=request.method,
                url=url,
                headers=headers,
                content=body if body else None,
            )
        except httpx.HTTPError as e:
            logger.error("proxy upstream error: target=%s err=%s", url, e)
            return JSONResponse(
                status_code=502,
                content={
                    "error": "UPSTREAM_UNREACHABLE",
                    "detail": f"Model service is unreachable at '{_model_service_url()}'.",
                },
            )

    # Keep response headers minimal/safe.
    resp_headers: dict[str, str] = {}
    for k, v in resp.headers.items():
        kl = k.lower()
        if kl in ("content-length", "transfer-encoding", "connection"):
            continue
        resp_headers[k] = v

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=resp_headers,
    )


@app.post("/generate")
async def generate(request: Request) -> Response:
    """
    Architecture endpoint: backend -> model-service.
    Pass-through to model service /generate.
    """
    return await _proxy(request, "/generate")


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"])
async def catch_all(request: Request, full_path: str) -> Response:
    """
    Proxy all other paths (/health, /stats, /api/v1/*, /billing/v1/*, etc.)
    so the existing frontend can keep using the original routes.
    """
    target_path = _normalize_target_path(f"/{full_path}")
    blocked = await _verify_org_header_or_block(request, target_path)
    if blocked is not None:
        return blocked
    return await _proxy(request, target_path)

