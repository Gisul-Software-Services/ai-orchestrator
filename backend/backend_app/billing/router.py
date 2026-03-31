from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from backend_app.billing.db import api_keys, aaptor_orgs, usage_logs

router = APIRouter(prefix="/billing/v1", tags=["billing"])


@router.get("/orgs/{org_id}/profile")
async def get_org_profile(org_id: str):
    """Read-only org record from Aaptor ``organization_db`` (for dashboards)."""
    doc = await aaptor_orgs().find_one({"orgId": org_id}, projection={"_id": 0})
    if not doc:
        raise HTTPException(404, f"Organization '{org_id}' not found")
    return {"org": doc}


@router.get("/orgs/{org_id}/usage/current")
async def get_current_usage(
    org_id: str,
    period: str | None = Query(default=None),
):
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    org_name = ""
    odoc = await aaptor_orgs().find_one({"orgId": org_id}, projection={"name": 1})
    if odoc:
        org_name = odoc.get("name") or ""
    pipeline = [
        {"$match": {"org_id": org_id, "billing_period": period}},
        {
            "$group": {
                "_id": None,
                "total_tokens": {"$sum": "$total_tokens"},
                "prompt_tokens": {"$sum": "$prompt_tokens"},
                "completion_tokens": {"$sum": "$completion_tokens"},
                "call_count": {"$sum": 1},
                "cache_hits": {"$sum": {"$cond": ["$cache_hit", 1, 0]}},
                "errors": {"$sum": {"$cond": [{"$eq": ["$status", "error"]}, 1, 0]}},
                "avg_latency_ms": {"$avg": "$latency_ms"},
            }
        },
    ]
    result = await usage_logs().aggregate(pipeline).to_list(1)
    if result:
        row = result[0]
        row.pop("_id", None)
        row["billing_period"] = period
        row["org_id"] = org_id
        row["org_name"] = org_name
        return row
    return {
        "org_id": org_id,
        "org_name": org_name,
        "total_tokens": 0,
        "prompt_tokens": 0,
        "completion_tokens": 0,
        "call_count": 0,
        "cache_hits": 0,
        "errors": 0,
        "avg_latency_ms": 0,
        "billing_period": period,
    }


@router.get("/orgs/{org_id}/usage/by-route")
async def get_usage_by_route(
    org_id: str,
    period: str | None = Query(default=None),
):
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    pipeline = [
        {"$match": {"org_id": org_id, "billing_period": period}},
        {
            "$group": {
                "_id": "$route",
                "total_tokens": {"$sum": "$total_tokens"},
                "call_count": {"$sum": 1},
                "cache_hits": {"$sum": {"$cond": ["$cache_hit", 1, 0]}},
                "avg_latency_ms": {"$avg": "$latency_ms"},
            }
        },
        {"$sort": {"total_tokens": -1}},
    ]
    rows = await usage_logs().aggregate(pipeline).to_list(100)
    return {"period": period, "org_id": org_id, "routes": rows}


@router.get("/orgs/{org_id}/usage/history")
async def get_usage_history(org_id: str):
    pipeline = [
        {"$match": {"org_id": org_id}},
        {
            "$group": {
                "_id": "$billing_period",
                "total_tokens": {"$sum": "$total_tokens"},
                "call_count": {"$sum": 1},
            }
        },
        {"$sort": {"_id": -1}},
    ]
    rows = await usage_logs().aggregate(pipeline).to_list(24)
    return {"org_id": org_id, "history": rows}


@router.get("/orgs/{org_id}/usage/logs")
async def get_usage_logs(
    org_id: str,
    period: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, le=200),
):
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    skip = (page - 1) * page_size
    cursor = (
        usage_logs()
        .find({"org_id": org_id, "billing_period": period}, projection={"_id": 0})
        .sort("created_at", -1)
        .skip(skip)
        .limit(page_size)
    )
    logs = await cursor.to_list(page_size)
    return {"org_id": org_id, "period": period, "page": page, "logs": logs}


@router.get("/orgs/{org_id}/dashboard")
async def get_org_dashboard(
    org_id: str,
    period: str | None = Query(default=None),
):
    """
    Single call for the org usage UI: Aaptor profile + current period aggregates
    + by-route breakdown + monthly history tail.
    """
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    profile = await aaptor_orgs().find_one({"orgId": org_id}, projection={"_id": 0})
    if not profile:
        raise HTTPException(404, f"Organization '{org_id}' not found")

    current = await get_current_usage(org_id, period=period)
    by_route = await get_usage_by_route(org_id, period=period)
    history = await get_usage_history(org_id)

    err_pipeline = [
        {
            "$match": {
                "org_id": org_id,
                "billing_period": period,
                "status": "error",
            }
        },
        {"$count": "n"},
    ]
    err_row = await usage_logs().aggregate(err_pipeline).to_list(1)
    errors_this_period = int(err_row[0]["n"]) if err_row else 0

    return {
        "org_id": org_id,
        "period": period,
        "profile": profile,
        "current": current,
        "by_route": by_route.get("routes", []),
        "history": history.get("history", []),
        "errors_this_period": errors_this_period,
    }


@router.get("/admin/usage")
async def get_all_orgs_usage(period: str | None = Query(default=None)):
    if not period:
        period = datetime.now(timezone.utc).strftime("%Y-%m")
    pipeline = [
        {"$match": {"billing_period": period}},
        {
            "$group": {
                "_id": "$org_id",
                "total_tokens": {"$sum": "$total_tokens"},
                "call_count": {"$sum": 1},
            }
        },
        {"$sort": {"total_tokens": -1}},
    ]
    rows = await usage_logs().aggregate(pipeline).to_list(500)
    return {"period": period, "orgs": rows}


async def _create_key(org_id: str, label: str) -> dict:
    org = await aaptor_orgs().find_one({"orgId": org_id})
    if not org:
        raise HTTPException(404, f"Org {org_id} not found in Aaptor")
    raw_key = secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    now = datetime.now(timezone.utc)
    await api_keys().insert_one(
        {
            "key_hash": key_hash,
            "org_id": org_id,
            "label": label,
            "status": "active",
            "last_used_at": None,
            "created_at": now,
        }
    )
    return {
        "org_id": org_id,
        "api_key": raw_key,
        "label": label,
        "note": "Store this key securely. It will not be shown again.",
    }


@router.post("/orgs/{org_id}/keys")
async def create_api_key(org_id: str, label: str = "default"):
    return await _create_key(org_id, label)


@router.post("/orgs/{org_id}/api-keys")
async def create_api_key_legacy(org_id: str, label: str = ""):
    """Backward-compatible alias for ``/keys``."""
    return await _create_key(org_id, label or "default")


@router.get("/orgs/{org_id}/keys")
async def list_api_keys(org_id: str):
    cursor = api_keys().find({"org_id": org_id}, projection={"_id": 0, "key_hash": 0})
    keys = await cursor.to_list(50)
    return {"org_id": org_id, "keys": keys}


@router.get("/orgs/{org_id}/api-keys")
async def list_api_keys_legacy(org_id: str):
    return await list_api_keys(org_id)


@router.delete("/orgs/{org_id}/keys/{key_hash}")
async def revoke_api_key(org_id: str, key_hash: str):
    result = await api_keys().update_one(
        {"org_id": org_id, "key_hash": key_hash},
        {"$set": {"status": "revoked", "revoked_at": datetime.now(timezone.utc)}},
    )
    if result.matched_count == 0:
        raise HTTPException(404, "Key not found")
    return {"status": "revoked"}
