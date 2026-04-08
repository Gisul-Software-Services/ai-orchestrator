"""
Model Console: GPU / inference / queue metrics (mounted at ``/api/v1``).
"""

from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter

from backend.model_app.core import state as app_state
from backend.model_app.services.jobs import _job_store_count_active, _job_store_count_total

router = APIRouter(prefix="/api/v1", tags=["dashboard"])


def _gpu_snapshot() -> Dict[str, Any]:
    try:
        import pynvml  # type: ignore

        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
        temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
        try:
            power = pynvml.nvmlDeviceGetPowerUsage(handle) / 1000.0
        except Exception:
            power = None
        pynvml.nvmlShutdown()
        used_mb = mem.used / (1024 * 1024)
        total_mb = mem.total / (1024 * 1024)
        return {
            "available": True,
            "error": None,
            "gpu_util_percent": float(util.gpu),
            "memory_used_percent": round(100.0 * mem.used / mem.total, 2) if mem.total else 0.0,
            "memory_used_mb": used_mb,
            "memory_total_mb": total_mb,
            "temperature_c": float(temp),
            "power_watts": power,
        }
    except Exception as e:
        return {
            "available": False,
            "error": str(e),
            "gpu_util_percent": None,
            "memory_used_percent": None,
            "memory_used_mb": None,
            "memory_total_mb": None,
            "temperature_c": None,
            "power_watts": None,
        }


@router.get("/metrics/gpu")
async def metrics_gpu():
    return _gpu_snapshot()


@router.get("/metrics/inference")
async def metrics_inference():
    st = app_state.STATS
    hits = st.get("cache_hits", 0)
    misses = st.get("cache_misses", 0)
    total = max(1, hits + misses)
    return {
        "total_requests": st.get("total_requests", 0),
        "cache_hits": hits,
        "cache_misses": misses,
        "cache_hit_rate_percent": round(100 * hits / total, 2),
        "requests_by_endpoint": dict(st.get("requests_by_endpoint", {})),
        "errors": st.get("errors", 0),
        "batches_processed": st.get("batches_processed", 0),
        "avg_batch_size": round(float(st.get("avg_batch_size", 0)), 4),
        "total_generation_time_seconds": round(float(st.get("total_generation_time", 0)), 2),
        "server_start_time": st.get("server_start_time"),
    }


async def _queues_payload() -> Dict[str, Any]:
    depths: Dict[str, int] = {k: len(v) for k, v in app_state.batch_queues.items()}
    try:
        active_jobs = await _job_store_count_active()
    except Exception:
        active_jobs = 0
    try:
        jobs_in_store = await _job_store_count_total()
    except Exception:
        jobs_in_store = 0
    return {
        "active_jobs": active_jobs,
        "jobs_in_store": jobs_in_store,
        "queue_depths": depths,
    }


@router.get("/metrics/queues")
async def metrics_queues():
    return await _queues_payload()


@router.get("/metrics/overview")
async def metrics_overview():
    """Single payload for the Next.js Monitoring page."""
    st = app_state.STATS
    hits = st.get("cache_hits", 0)
    misses = st.get("cache_misses", 0)
    total = max(1, hits + misses)
    cuda_gb = None
    if app_state.llm is not None:
        try:
            import torch

            cuda_gb = round(torch.cuda.memory_allocated() / (1024**3), 3)
        except Exception:
            pass

    q = await _queues_payload()
    g = _gpu_snapshot()
    return {
        "model_loaded": app_state.llm is not None,
        "cuda_memory_gb": cuda_gb,
        "gpu": g,
        "inference": {
            "total_requests": st.get("total_requests", 0),
            "cache_hit_rate_percent": round(100 * hits / total, 2),
            "requests_by_endpoint": dict(st.get("requests_by_endpoint", {})),
        },
        "queues": q,
    }
