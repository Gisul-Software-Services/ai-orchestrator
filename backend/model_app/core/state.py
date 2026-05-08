from __future__ import annotations

import asyncio
from collections import deque

STATS = {
    "total_requests": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_generation_time": 0.0,
    "requests_by_endpoint": {},
    "errors": 0,
    "batches_processed": 0,
    "total_batched_requests": 0,
    "avg_batch_size": 0.0,
    "server_start_time": None,
}

batch_queues = {
    "topics": deque(),
    "mcq": deque(),
    "subjective": deque(),
    "coding": deque(),
    "sql": deque(),
    "aiml": deque(),
}

batch_locks = {endpoint: asyncio.Lock() for endpoint in batch_queues.keys()}
pending_results = {}

# Model Console: recent /api access rows (middleware)
REQUEST_LOG = deque(maxlen=1000)

llm = None
coder_llm = None

# ── LLM Concurrency Control ──────────────────────────────────────────────────
# Controls how many LLM requests run simultaneously.
# Single 8GB GPU: LLM_CONCURRENCY = 1
# Multi-GPU or larger GPU: increase LLM_CONCURRENCY to match GPU count
# This is the ONLY value to change when scaling to more GPUs.
import os
LLM_CONCURRENCY: int = int(os.getenv("LLM_CONCURRENCY", "1"))

# Global semaphore — serializes ALL LLM calls (generation + evaluation).
# Covers: SQL generation, DSA eval, SQL eval, AIML eval, DevOps eval, Cloud eval.
# With LLM_CONCURRENCY=1: one request at a time (8GB GPU safe).
# With LLM_CONCURRENCY=N: N concurrent requests (for N GPUs or larger GPU).
llm_semaphore: asyncio.Semaphore = asyncio.Semaphore(LLM_CONCURRENCY)
