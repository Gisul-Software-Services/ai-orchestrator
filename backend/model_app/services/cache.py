from __future__ import annotations

import hashlib
import json
from typing import Any

from cachetools import TTLCache

from backend.model_app.core.state import STATS


RESPONSE_CACHE = TTLCache(maxsize=1000, ttl=3600)


def generate_cache_key(endpoint: str, data: dict) -> str:
    payload = data.copy()
    request_id = payload.pop("request_id", None)
    payload.pop("use_cache", None)
    base = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
    if request_id:
        base += f":{request_id}"
    return hashlib.md5(base.encode()).hexdigest()


def get_from_cache(cache_key: str) -> Any:
    if cache_key in RESPONSE_CACHE:
        STATS["cache_hits"] += 1
        return RESPONSE_CACHE[cache_key]
    STATS["cache_misses"] += 1
    return None


def save_to_cache(cache_key: str, response: Any) -> None:
    RESPONSE_CACHE[cache_key] = response
