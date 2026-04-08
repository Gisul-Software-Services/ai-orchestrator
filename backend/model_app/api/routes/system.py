"""System routes for the modular monolith."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Query

from backend.model_app.core.state import REQUEST_LOG
from backend.model_app.services import system as system_service

router = APIRouter(tags=["system"])


@router.get("/api/v1/job/{job_id}")
async def poll_job(job_id: str):
    return await system_service.poll_job(job_id)


@router.get("/")
async def root():
    return system_service.root()


@router.get("/health")
async def health_check():
    return await system_service.health_check()


@router.get("/stats")
async def get_stats():
    return system_service.get_stats()


@router.post("/api/v1/clear-cache")
async def clear_cache():
    return system_service.clear_cache()


@router.get("/api/v1/request-log")
async def get_request_log(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    endpoint: str | None = Query(default=None),
    org_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    start_date: str | None = Query(default=None),
    end_date: str | None = Query(default=None),
    sort_by: str = Query(default="timestamp"),
    sort_order: str = Query(default="desc"),
):
    items: list[dict[str, Any]] = list(REQUEST_LOG)

    if endpoint:
        q = endpoint.lower().strip()
        items = [x for x in items if q in str(x.get("path", "")).lower()]

    if org_id:
        oid = org_id.strip().lower()
        items = [x for x in items if str(x.get("org_id", "")).lower() == oid]

    if status == "success":
        items = [x for x in items if int(x.get("status_code", 0)) < 400]
    elif status == "error":
        items = [x for x in items if int(x.get("status_code", 0)) >= 400]

    def _parse_dt(v: str | None) -> datetime | None:
        if not v:
            return None
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00"))
        except Exception:
            return None

    start_dt = _parse_dt(start_date)
    end_dt = _parse_dt(end_date)

    if start_dt or end_dt:
        filtered: list[dict[str, Any]] = []
        for item in items:
            ts = _parse_dt(str(item.get("timestamp", "")))
            if ts is None:
                continue
            if start_dt and ts < start_dt:
                continue
            if end_dt and ts > end_dt:
                continue
            filtered.append(item)
        items = filtered

    reverse = sort_order != "asc"
    if sort_by == "latency_ms":
        items = sorted(items, key=lambda x: int(x.get("latency_ms", 0)), reverse=reverse)
    else:
        items = sorted(items, key=lambda x: str(x.get("timestamp", "")), reverse=reverse)

    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    paged = items[start:end]

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": paged,
    }
