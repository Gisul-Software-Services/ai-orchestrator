"""
Capture request/org context once per generation job (snapshot at enqueue time).
"""

from __future__ import annotations

from typing import Any

from starlette.requests import Request


def _client_host(request: Request) -> str:
    forwarded = (request.headers.get("x-forwarded-for") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:128]
    if request.client and request.client.host:
        return request.client.host[:128]
    return ""


def snapshot_usage_meta(request: Request | None) -> dict[str, Any]:
    """Immutable-ish dict for background metering (capture before request is recycled)."""
    if request is None:
        return {
            "org_id": "unattributed",
            "org_name": "",
            "org_verified": False,
            "client_ip": "",
            "user_agent": "",
            "correlation_id": "",
        }
    st = request.state
    return {
        "org_id": getattr(st, "org_id", "unattributed") or "unattributed",
        "org_name": (getattr(st, "org_name", "") or "")[:256],
        "org_verified": bool(getattr(st, "org_verified", False)),
        "client_ip": _client_host(request),
        "user_agent": (request.headers.get("user-agent") or "")[:512],
        "correlation_id": (request.headers.get("x-request-id") or request.headers.get("X-Request-Id") or "")[:128],
    }
