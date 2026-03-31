from __future__ import annotations

import os
from typing import Iterable

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response

app = FastAPI(title="Gisul Backend API (Lightweight)")


def _model_service_url() -> str:
    # Points to the model service base URL (scheme + host + port), no trailing slash.
    return os.environ.get("MODEL_SERVICE_URL", "http://model-service:7001").rstrip("/")


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
    return target_path


async def _proxy(request: Request, target_path: str) -> Response:
    url = f"{_model_service_url()}{target_path}"
    if request.url.query:
        url = f"{url}?{request.url.query}"

    headers = _filtered_headers(request.headers.items())
    body = await request.body()

    async with httpx.AsyncClient(timeout=httpx.Timeout(600.0)) as client:
        resp = await client.request(
            method=request.method,
            url=url,
            headers=headers,
            content=body if body else None,
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
    return await _proxy(request, target_path)

