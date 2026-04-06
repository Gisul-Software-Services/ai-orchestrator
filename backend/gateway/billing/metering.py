"""Gateway usage metadata capture only (no usage_logs writes)."""

from __future__ import annotations

import base64
import json
from contextvars import ContextVar
from typing import Any

from starlette.requests import Request

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


def encode_usage_meta_header(meta: dict[str, Any]) -> str:
    raw = json.dumps(meta, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def get_usage_meta_header_value(request: Request | None) -> str:
    return encode_usage_meta_header(bind_usage_meta_from_request(request))
