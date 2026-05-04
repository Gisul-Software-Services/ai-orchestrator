"""
RAG Service client for gisul_model.

Calls the aaptor-rag-service (port 7003) for FAISS-based retrieval.
Falls back to local assets if the RAG service is unavailable.
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_RAG_TIMEOUT = httpx.Timeout(connect=2.0, read=10.0, write=5.0, pool=2.0)


def _rag_service_url() -> str:
    from backend.model_app.core.settings import get_settings
    s = get_settings()
    return getattr(s, "rag_service_url", "").rstrip("/")


async def retrieve(
    competency: str,
    topic: str,
    difficulty: str,
    concepts: list[str],
    top_k: int = 20,
) -> dict | None:
    """
    Call RAG service to retrieve best matching entry.
    Returns None if RAG service is unavailable (caller falls back to local).
    """
    url = _rag_service_url()
    if not url:
        return None

    try:
        async with httpx.AsyncClient(timeout=_RAG_TIMEOUT) as client:
            resp = await client.post(
                f"{url}/api/v1/retrieve",
                json={
                    "competency": competency,
                    "topic": topic,
                    "difficulty": difficulty,
                    "concepts": concepts,
                    "top_k": top_k,
                },
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None
            else:
                logger.warning("RAG service returned %s for %s/%s", resp.status_code, competency, topic)
                return None
    except Exception as e:
        logger.warning("RAG service unavailable (%s) — falling back to local", e)
        return None


async def retrieve_bulk(
    competency: str,
    topic: str,
    difficulty: str,
    concepts: list[str],
    count: int = 5,
) -> list[dict]:
    """
    Call RAG service to retrieve N different matching entries for bulk generation.
    Returns empty list if RAG service is unavailable.
    """
    url = _rag_service_url()
    if not url:
        return []

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(connect=2.0, read=30.0, write=5.0, pool=2.0)) as client:
            resp = await client.post(
                f"{url}/api/v1/retrieve/bulk",
                json={
                    "competency": competency,
                    "topic": topic,
                    "difficulty": difficulty,
                    "concepts": concepts,
                    "count": count,
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("matches", [])
            else:
                logger.warning("RAG bulk returned %s for %s/%s", resp.status_code, competency, topic)
                return []
    except Exception as e:
        logger.warning("RAG bulk unavailable (%s) — falling back to local", e)
        return []
