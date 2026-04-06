"""Token capture + usage persistence for model app."""

from __future__ import annotations

import asyncio
import base64
import json
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request

from backend.model_app.billing.db import usage_logs
from backend.model_app.core.settings import get_settings

current_token_counts: ContextVar[dict | None] = ContextVar("current_token_counts", default=None)
current_usage_meta: ContextVar[dict[str, Any] | None] = ContextVar("current_usage_meta", default=None)


def snapshot_usage_meta(request: Request | None) -> dict[str, Any]:
    if request is None:
        return {
            "org_id": "unattributed",
            "org_name": "",
            "org_verified": False,
            "client_ip": "",
            "user_agent": "",
            "correlation_id": "",
        }
    header_meta = request.headers.get("x-usage-meta", "").strip()
    if header_meta:
        try:
            decoded = base64.b64decode(header_meta.encode("ascii"), validate=True).decode("utf-8")
            payload = json.loads(decoded)
            if isinstance(payload, dict):
                return {
                    "org_id": str(payload.get("org_id") or "unattributed"),
                    "org_name": str(payload.get("org_name") or ""),
                    "org_verified": bool(payload.get("org_verified", False)),
                    "client_ip": str(payload.get("client_ip") or ""),
                    "user_agent": str(payload.get("user_agent") or ""),
                    "correlation_id": str(payload.get("correlation_id") or ""),
                }
        except Exception:
            pass

    return {
        "org_id": getattr(request.state, "org_id", "unattributed") or "unattributed",
        "org_name": getattr(request.state, "org_name", "") or "",
        "org_verified": bool(getattr(request.state, "org_verified", False)),
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("user-agent", ""),
        "correlation_id": request.headers.get("x-correlation-id", ""),
    }


def bind_usage_meta_from_request(request: Request | None) -> dict[str, Any]:
    meta = snapshot_usage_meta(request)
    current_usage_meta.set(meta)
    return meta


def peek_usage_meta() -> dict[str, Any]:
    v = current_usage_meta.get(None)
    return dict(v) if isinstance(v, dict) else {}


async def record_usage(**kwargs) -> None:
    now = datetime.now(timezone.utc)
    doc = {
        "request_id": kwargs["request_id"],
        "org_id": kwargs.get("org_id", "unattributed"),
        "org_name": (kwargs.get("org_name") or "")[:256],
        "org_verified": bool(kwargs.get("org_verified", False)),
        "job_id": kwargs.get("job_id", ""),
        "route": kwargs.get("route", ""),
        "prompt_tokens": int(kwargs.get("prompt_tokens", 0)),
        "completion_tokens": int(kwargs.get("completion_tokens", 0)),
        "total_tokens": int(kwargs.get("total_tokens", 0)),
        "cache_hit": bool(kwargs.get("cache_hit", False)),
        "latency_ms": int(kwargs.get("latency_ms", 0)),
        "status": kwargs.get("status", "success"),
        "billing_period": now.strftime("%Y-%m"),
        "created_at": now,
        "client_ip": (kwargs.get("client_ip") or "")[:128],
        "user_agent": (kwargs.get("user_agent") or "")[:512],
        "correlation_id": (kwargs.get("correlation_id") or "")[:128],
        "model_name": (kwargs.get("model_name") or "")[:128],
        "api_version": (kwargs.get("api_version") or "")[:32],
        "http_method": "POST",
    }
    err = kwargs.get("error_detail")
    if err:
        doc["error_detail"] = str(err)[:500]
    try:
        await usage_logs().update_one({"request_id": doc["request_id"]}, {"$setOnInsert": doc}, upsert=True)
    except Exception:
        pass


async def emit_usage_after_job(
    *,
    job_id: str,
    usage_meta: dict[str, Any] | None,
    route: str,
    cache_hit: bool,
    latency_ms: float,
    status: str = "success",
    error_detail: str | None = None,
) -> None:
    try:
        counts = current_token_counts.get(None) or {}
        meta = usage_meta if usage_meta is not None else peek_usage_meta() or snapshot_usage_meta(None)
        s = get_settings()
        await record_usage(
            request_id=job_id,
            org_id=str(meta.get("org_id") or "unattributed"),
            job_id=job_id,
            route=route,
            prompt_tokens=int(counts.get("prompt_tokens", 0)),
            completion_tokens=int(counts.get("completion_tokens", 0)),
            total_tokens=int(counts.get("total_tokens", 0)),
            cache_hit=cache_hit,
            latency_ms=int(round(latency_ms)),
            status=status,
            org_name=str(meta.get("org_name") or ""),
            org_verified=bool(meta.get("org_verified")),
            client_ip=str(meta.get("client_ip") or ""),
            user_agent=str(meta.get("user_agent") or ""),
            correlation_id=str(meta.get("correlation_id") or ""),
            model_name=s.model_name,
            api_version=s.api_version,
            error_detail=error_detail,
        )
    except Exception:
        pass


def schedule_usage_emit(**kwargs) -> None:
    try:
        async def _run() -> None:
            await emit_usage_after_job(**kwargs)

        asyncio.create_task(_run())
    except Exception:
        pass
