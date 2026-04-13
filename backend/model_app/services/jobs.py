from __future__ import annotations

import fnmatch
import json

import redis.asyncio as redis_asyncio


_redis_client: redis_asyncio.Redis | None = None
JOB_TTL_SECONDS = 3600


def _get_redis_client() -> redis_asyncio.Redis:
    global _redis_client
    if _redis_client is None:
        from backend.model_app.core.settings import get_settings

        _redis_client = redis_asyncio.from_url(get_settings().redis_url, decode_responses=True)
    return _redis_client


def _job_key(job_id: str) -> str:
    return f"job:{job_id}"


async def _job_store_set(job_id: str, payload: dict) -> None:
    r = _get_redis_client()
    await r.set(_job_key(job_id), json.dumps(payload), ex=JOB_TTL_SECONDS)


async def _job_store_get(job_id: str) -> dict | None:
    r = _get_redis_client()
    raw = await r.get(_job_key(job_id))
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


async def _job_store_exists(job_id: str) -> bool:
    r = _get_redis_client()
    return bool(await r.exists(_job_key(job_id)))


async def _job_store_update(job_id: str, **fields) -> None:
    current = await _job_store_get(job_id) or {}
    current.update(fields)
    await _job_store_set(job_id, current)


async def _job_store_count_total() -> int:
    r = _get_redis_client()
    total = 0
    async for key in r.scan_iter(match="job:*", count=1000):
        if fnmatch.fnmatch(str(key), "job:*"):
            total += 1
    return total


async def _job_store_count_active() -> int:
    r = _get_redis_client()
    n = 0
    async for key in r.scan_iter(match="job:*", count=1000):
        raw = await r.get(key)
        if not raw:
            continue
        try:
            doc = json.loads(raw)
        except Exception:
            continue
        if isinstance(doc, dict) and doc.get("status") in ("pending", "processing"):
            n += 1
    return n
