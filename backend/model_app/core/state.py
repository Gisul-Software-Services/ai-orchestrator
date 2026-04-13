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
