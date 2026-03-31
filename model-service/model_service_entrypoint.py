from __future__ import annotations

import os
import asyncio
import time
from typing import Any, Dict, Optional

import httpx
from fastapi import Request
from pydantic import BaseModel, Field

# Reuse the existing heavy monolith app for all /api/v1 and /billing/v1 routes.
from backend_app.main import app as core_app


def _assets_dir() -> str:
    # model-service runs from /app in the Dockerfile.
    return os.environ.get("ASSETS_DIR", "/app/assets")


@core_app.on_event("startup")
def _startup_preload_indexes() -> None:
    """
    Best-effort FAISS preload.
    The monolith already supports lazy loading with fallback; we preload so the first request is faster.
    """
    try:
        os.environ.setdefault("ASSETS_DIR", _assets_dir())

        from backend_app.engine import core as eng

        # These are internal helpers in engine/core.py.
        if hasattr(eng, "_load_faiss_index"):
            eng._load_faiss_index()
        if hasattr(eng, "_load_aiml_faiss"):
            eng._load_aiml_faiss()
    except Exception:
        # Never fail startup.
        pass


class GenerateRequest(BaseModel):
    endpoint: str = Field(
        ...,
        description="Existing monolith endpoint id without /api/v1 prefix (e.g. generate-mcq)",
    )
    body: Dict[str, Any] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=600, ge=10, le=3600)
    poll_interval_seconds: float = Field(default=2.0, ge=0.25, le=10.0)


@core_app.post("/generate")
async def generate_via_monolith_jobs(req: GenerateRequest, request: Request):
    """
    Model-service architecture endpoint.
    Calls the existing monolith's /api/v1/{endpoint} job-creation route, then polls /api/v1/job/{id}.
    """
    model_self_url = os.environ.get("MODEL_SERVICE_SELF_URL", "http://127.0.0.1:7001")
    create_url = f"{model_self_url}/api/v1/{req.endpoint}"

    headers_to_forward: Dict[str, str] = {}
    for k, v in request.headers.items():
        lk = k.lower()
        if lk.startswith("x-") or lk in ("user-agent", "content-type"):
            headers_to_forward[k] = v

    async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
        t0 = time.time()
        r = await client.post(create_url, json=req.body, headers=headers_to_forward)
        r.raise_for_status()
        data = r.json()

        job_id = data.get("job_id")
        if not job_id:
            # Some endpoints may respond with complete payload directly.
            return data

        deadline = t0 + req.timeout_seconds
        while time.time() < deadline:
            job_r = await client.get(
                f"{model_self_url}/api/v1/job/{job_id}",
                headers=headers_to_forward,
            )
            job_r.raise_for_status()
            job = job_r.json()
            status = job.get("status")

            if status == "complete":
                if "result" in job:
                    return job["result"]
                return job

            if status in ("failed", "error"):
                return {"status": status, "error": job.get("error")}

            await asyncio.sleep(req.poll_interval_seconds)

    raise RuntimeError("Timed out waiting for /generate job completion")


# Export `app` for uvicorn.
app = core_app

