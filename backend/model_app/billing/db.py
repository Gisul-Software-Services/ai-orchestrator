from __future__ import annotations

from motor.motor_asyncio import AsyncIOMotorClient

from backend.model_app.core.settings import get_settings

_client: AsyncIOMotorClient | None = None


def get_client() -> AsyncIOMotorClient:
    global _client
    if _client is None:
        _client = AsyncIOMotorClient(get_settings().mongodb_uri)
    return _client


def usage_logs():
    return get_client()[get_settings().billing_db_name]["usage_logs"]


def api_keys():
    return get_client()[get_settings().billing_db_name]["api_keys"]


async def ensure_indexes() -> None:
    await usage_logs().create_index("request_id", unique=True)
    await usage_logs().create_index([("org_id", 1), ("billing_period", -1)])
    await usage_logs().create_index([("org_id", 1), ("route", 1), ("billing_period", -1)])
    await usage_logs().create_index([("org_id", 1), ("created_at", -1)])
    await usage_logs().create_index([("correlation_id", 1)])
    await usage_logs().create_index([("status", 1), ("billing_period", -1)])
    await api_keys().create_index("key_hash", unique=True)
    await api_keys().create_index("org_id")
