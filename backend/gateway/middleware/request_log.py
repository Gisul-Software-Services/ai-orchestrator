"""Append request access records to the shared in-memory request log."""
"""Append request access records for traffic that hits this gateway process.

The model service keeps a separate in-memory log in ``engine.core`` when requests
reach it (including proxied calls). The gateway image must not import ``model_app``
(it would pull torch/vLLM and break the slim container).
"""

from __future__ import annotations

import json
import time
import uuid
from collections import deque
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

GATEWAY_REQUEST_LOG: deque[dict] = deque(maxlen=1000)


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        cache_hit_header = (
            response.headers.get("x-cache-hit")
            or response.headers.get("cache-hit")
            or response.headers.get("x-cache")
        )
        if isinstance(cache_hit_header, str):
            cache_hit = cache_hit_header.strip().lower() in {"1", "true", "yes", "hit"}
        else:
            cache_hit = bool(getattr(request.state, "cache_hit", False))

        job_id = None
        try:
            raw = getattr(response, "body", None)
            if isinstance(raw, (bytes, bytearray)) and raw:
                payload = json.loads(raw.decode("utf-8"))
                if isinstance(payload, dict):
                    jid = payload.get("job_id")
                    job_id = str(jid) if jid is not None else None
        except Exception:
            job_id = None

        record = {
            "request_id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "org_id": getattr(request.state, "org_id", None) or "unattributed",
            "status_code": response.status_code,
            "latency_ms": int(round(duration_ms)),
            "cache_hit": bool(cache_hit),
            "job_id": job_id,
        }
        GATEWAY_REQUEST_LOG.appendleft(record)
        return response
