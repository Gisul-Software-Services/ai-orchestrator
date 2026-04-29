from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

import redis.asyncio as redis_asyncio

from backend.model_app.core.state import STATS

logger = logging.getLogger(__name__)

CACHE_TTL_SECONDS = 3600
_CACHE_KEY_PREFIX = "cache:"

_redis_client: redis_asyncio.Redis | None = None


def _get_redis_client() -> redis_asyncio.Redis:
    global _redis_client
    if _redis_client is None:
        from backend.model_app.core.settings import get_settings
        _redis_client = redis_asyncio.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


def generate_cache_key(endpoint: str, data: dict) -> str:
    payload = data.copy()
    request_id = payload.pop("request_id", None)
    payload.pop("use_cache", None)
    base = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
    if request_id:
        base += f":{request_id}"
    return hashlib.md5(base.encode()).hexdigest()


def _redis_cache_key(cache_key: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{cache_key}"


async def get_from_cache_async(cache_key: str) -> Any:
    """Async Redis-backed cache lookup."""
    try:
        r = _get_redis_client()
        raw = await r.get(_redis_cache_key(cache_key))
        if raw:
            STATS["cache_hits"] += 1
            return json.loads(raw)
    except Exception as e:
        logger.warning("Cache get failed for key %s: %s", cache_key, e)
    STATS["cache_misses"] += 1
    return None


async def save_to_cache_async(cache_key: str, response: Any) -> None:
    """Async Redis-backed cache save."""
    try:
        r = _get_redis_client()
        await r.set(
            _redis_cache_key(cache_key),
            json.dumps(response, default=str),
            ex=CACHE_TTL_SECONDS,
        )
    except Exception as e:
        logger.warning("Cache save failed for key %s: %s", cache_key, e)

