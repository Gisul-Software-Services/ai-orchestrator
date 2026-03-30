"""Append lightweight access records to ``gisul.engine.core.REQUEST_LOG``."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from gisul.engine import core as engine_core


class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        if not request.url.path.startswith("/api"):
            return await call_next(request)

        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000

        record = {
            "id": str(uuid.uuid4())[:12],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "method": request.method,
            "path": request.url.path,
            "query": request.url.query or None,
            "status_code": response.status_code,
            "duration_ms": round(duration_ms, 2),
        }
        engine_core.REQUEST_LOG.appendleft(record)
        return response
