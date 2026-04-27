"""Generation routes for the modular monolith (MCQ, SQL, coding, topics, chat)."""
from __future__ import annotations

from fastapi import APIRouter, Body
from starlette.requests import Request

from backend.model_app.schemas.generation import (
    CodingGenerationRequest,
    MCQGenerationRequest,
    SQLGenerationRequest,
    SubjectiveGenerationRequest,
    TopicGenerationRequest,
)
from backend.model_app.services import generation as generation_service

router = APIRouter(tags=["generation"])
generation_router = router


@router.post("/api/v1/generate-topics")
async def generate_topics(body: TopicGenerationRequest, http_request: Request):
    return await generation_service.generate_topics(body, http_request)


@router.post("/api/v1/generate-mcq")
async def generate_mcq(body: MCQGenerationRequest, http_request: Request):
    return await generation_service.generate_mcq(body, http_request)


@router.post("/api/v1/generate-subjective")
async def generate_subjective(body: SubjectiveGenerationRequest, http_request: Request):
    return await generation_service.generate_subjective(body, http_request)


@router.post("/api/v1/generate-coding")
async def generate_coding(body: CodingGenerationRequest, http_request: Request):
    return await generation_service.generate_coding(body, http_request)


@router.post("/api/v1/generate-sql")
async def generate_sql(body: SQLGenerationRequest, http_request: Request):
    return await generation_service.generate_sql(body, http_request)


@router.post("/api/v1/chat")
async def chat(
    http_request: Request,
    payload: dict = Body(...),
):
    """
    Generic chat endpoint — accepts messages array and runs Qwen directly.
    Used by Aaptor to send aptor_shared prompts to Qwen.
    Same interface as OpenAI chat completions.

    Body:
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."}
        ],
        "max_tokens": 900,
        "temperature": 0.7
    }
    """
    from backend.model_app.billing.metering import bind_usage_meta_from_request
    from backend.model_app.services.model import _llm_chat_single

    bind_usage_meta_from_request(http_request)

    messages = payload.get("messages", [])
    max_tokens = int(payload.get("max_tokens", 900))
    temperature = float(payload.get("temperature", 0.7))

    if not messages:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="messages array is required")

    text, prompt_tokens, completion_tokens = _llm_chat_single(
        messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return {
        "text": text,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
        "model": "qwen",
    }

