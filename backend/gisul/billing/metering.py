"""
Writes usage rows to ``gisul_billing.usage_logs`` after generation completes.
Fire-and-forget; idempotent on ``request_id`` via upsert + ``$setOnInsert``.
"""

from __future__ import annotations

import asyncio
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from starlette.requests import Request

from gisul.billing.db import usage_logs

current_token_counts: ContextVar[dict | None] = ContextVar(
    "current_token_counts", default=None
)

current_usage_meta: ContextVar[dict[str, Any] | None] = ContextVar(
    "current_usage_meta", default=None
)


def bind_usage_meta_from_request(request: Request | None) -> dict[str, Any]:
    """Snapshot org + client metadata at enqueue time; copy propagates to asyncio tasks."""
    from gisul.billing.usage_meta import snapshot_usage_meta

    meta = snapshot_usage_meta(request)
    current_usage_meta.set(meta)
    return meta


def peek_usage_meta() -> dict[str, Any]:
    v = current_usage_meta.get(None)
    return dict(v) if isinstance(v, dict) else {}


def get_token_counts() -> dict:
    v = current_token_counts.get(None)
    return dict(v) if isinstance(v, dict) else {}


async def record_usage(
    *,
    request_id: str,
    org_id: str,
    job_id: str,
    route: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    cache_hit: bool,
    latency_ms: int,
    status: str,
    org_name: str = "",
    org_verified: bool = False,
    client_ip: str = "",
    user_agent: str = "",
    correlation_id: str = "",
    model_name: str = "",
    api_version: str = "",
    error_detail: str | None = None,
) -> None:
    now = datetime.now(timezone.utc)
    err = (error_detail or "")[:500] if error_detail else None
    doc = {
        "request_id": request_id,
        "org_id": org_id,
        "org_name": (org_name or "")[:256],
        "org_verified": bool(org_verified),
        "job_id": job_id,
        "route": route,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
        "cache_hit": cache_hit,
        "latency_ms": latency_ms,
        "status": status,
        "billing_period": now.strftime("%Y-%m"),
        "created_at": now,
        "client_ip": (client_ip or "")[:128],
        "user_agent": (user_agent or "")[:512],
        "correlation_id": (correlation_id or "")[:128],
        "model_name": (model_name or "")[:128],
        "api_version": (api_version or "")[:32],
        "http_method": "POST",
    }
    if err:
        doc["error_detail"] = err
    try:
        await usage_logs().update_one(
            {"request_id": request_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
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
    """Read org snapshot + token counts; write usage log. Never raises."""
    try:
        from gisul.billing.usage_meta import snapshot_usage_meta
        from gisul.core.settings import get_settings

        counts = current_token_counts.get(None) or {}
        meta: dict[str, Any]
        if usage_meta is not None:
            meta = usage_meta
        else:
            meta = peek_usage_meta()
            if not meta:
                meta = snapshot_usage_meta(None)

        org_id = str(meta.get("org_id") or "unattributed")
        s = get_settings()
        await record_usage(
            request_id=job_id,
            org_id=org_id,
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


def schedule_usage_emit(
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

        async def _run() -> None:
            await emit_usage_after_job(
                job_id=job_id,
                usage_meta=usage_meta,
                route=route,
                cache_hit=cache_hit,
                latency_ms=latency_ms,
                status=status,
                error_detail=error_detail,
            )

        asyncio.create_task(_run())
    except Exception:
        pass
