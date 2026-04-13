"""System/service orchestration layer."""

from __future__ import annotations

import logging

from fastapi import HTTPException
import torch

from backend.model_app.core import state as app_state
from backend.model_app.services.cache import RESPONSE_CACHE
from backend.model_app.services.jobs import (
    _job_store_count_active,
    _job_store_count_total,
    _job_store_exists,
    _job_store_get,
)


logger = logging.getLogger(__name__)


async def poll_job(job_id: str):
    if not await _job_store_exists(job_id):
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")
    return await _job_store_get(job_id)


def root():
    return {
        "service": "Qwen API - Production Hardened",
        "version": "9.0.0",
        "v8_changes": [
            "FEAT: All endpoints now support num_questions (int, default=1) for bulk generation",
            "FEAT: All endpoints return list-based batch responses (questions/coding_problems/sql_problems/aiml_problems)",
            "FEAT: Per-item cache keys include question_index to prevent identical cached results across slots",
            "FEAT: POST /api/v1/clear-cache endpoint to flush entire response cache on demand",
            "FEAT: use_cache=False bypasses cache per-request, forcing fresh generation for every item",
            "FEAT: TopicBatchResponse / MCQBatchResponse / SubjectiveBatchResponse / CodingBatchResponse / SQLBatchResponse / AIMLBatchResponse models added",
        ],
        "v7_changes": [
            "FIX ROUTING: _CODE_TOPIC_KEYWORDS narrowed to execution-specific signals only",
        ],
        "v6_fixes": [
            "FIX1: verify_mcq_with_llm now raises on rejected:true from verifier",
            "FIX2: safe_execute uses minimal PATH env instead of env={} (fixes Linux crash)",
            "FIX3: Added from-import pattern to blocked code patterns",
            "FIX4: explanation_mismatch changed to skip (not reject) to avoid false retries",
            "FIX5: extract_json only calls AIML validation when dataset key present",
            "FIX6: build_mcq_prompt has domain-aware rules for 12+ tech domains",
        ],
    }


async def health_check():
    active_jobs = await _job_store_count_active()
    return {
        "status": "healthy",
        "model_loaded": app_state.llm is not None,
        "memory_gb": torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0,
        "queue_sizes": {e: len(q) for e, q in app_state.batch_queues.items()},
        "active_jobs": active_jobs,
        "total_jobs_in_store": await _job_store_count_total(),
    }


def get_stats():
    cache_hit_rate = (
        app_state.STATS["cache_hits"]
        / max(1, app_state.STATS["cache_hits"] + app_state.STATS["cache_misses"])
    ) * 100
    return {
        "total_requests": app_state.STATS["total_requests"],
        "cache_hit_rate_percent": round(cache_hit_rate, 2),
        "requests_by_endpoint": app_state.STATS["requests_by_endpoint"],
        "batches_processed": app_state.STATS["batches_processed"],
        "avg_batch_size": round(app_state.STATS["avg_batch_size"], 2),
        "errors": app_state.STATS["errors"],
    }


def clear_cache():
    cleared_count = len(RESPONSE_CACHE)
    RESPONSE_CACHE.clear()
    logger.info("Cache cleared: %s entries removed", cleared_count)
    return {
        "status": "cache cleared",
        "entries_removed": cleared_count,
        "message": f"Successfully cleared {cleared_count} cached response(s)",
    }
