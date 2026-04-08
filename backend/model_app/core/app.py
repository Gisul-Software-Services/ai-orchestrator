from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI

from backend.model_app.billing.metering import schedule_usage_emit
from backend.model_app.core import state as app_state
from backend.model_app.services.model import load_model


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def _batch_size_max() -> int:
    from backend.model_app.core.settings import get_settings

    return max(1, get_settings().batch_size_max)


def _batch_timeout() -> float:
    from backend.model_app.core.settings import get_settings

    return float(get_settings().batch_timeout)


def _emit_usage_metering(
    *,
    job_id: str,
    usage_meta: dict | None,
    route: str,
    cache_hit: bool,
    latency_ms: float,
    status: str = "success",
    error_detail: str | None = None,
) -> None:
    try:
        schedule_usage_emit(
            job_id=job_id,
            usage_meta=usage_meta,
            route=route,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
            status=status,
            error_detail=error_detail,
        )
    except Exception:
        pass


@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    from backend.model_app.billing.db import ensure_indexes
    from backend.model_app.core.settings import get_settings

    s = get_settings()
    for p in (s.dsa_enriched_path, s.aiml_catalog_path):
        if not p.exists():
            raise RuntimeError(f"Required asset not found: {p}")
    await ensure_indexes()
    app_state.STATS["server_start_time"] = datetime.now(timezone.utc).isoformat()
    load_model()
    yield
    for q in app_state.batch_queues.values():
        q.clear()


app = FastAPI(title="Gisul AI Platform", version="2.0.0", lifespan=_app_lifespan)

__all__ = [
    "app",
    "logger",
    "_batch_size_max",
    "_batch_timeout",
    "_emit_usage_metering",
]
