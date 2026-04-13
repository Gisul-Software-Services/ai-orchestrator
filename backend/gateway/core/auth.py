from __future__ import annotations

import hmac

from fastapi import HTTPException, Request

from backend.gateway.core.settings import get_settings


def get_admin_api_key() -> str:
    return (get_settings().admin_api_key or "").strip()


def is_admin_api_key(raw_key: str | None) -> bool:
    candidate = (raw_key or "").strip()
    expected = get_admin_api_key()
    if not candidate or not expected:
        return False
    return hmac.compare_digest(candidate, expected)


async def require_admin_api_key(request: Request) -> None:
    if is_admin_api_key(request.headers.get("X-Api-Key")):
        return
    raise HTTPException(
        status_code=401,
        detail={
            "error": "ADMIN_AUTH_REQUIRED",
            "detail": "A valid admin API key is required for this endpoint.",
        },
    )
