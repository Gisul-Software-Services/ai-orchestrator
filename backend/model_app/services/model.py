from __future__ import annotations

import logging

from vllm import LLM, SamplingParams

from backend.model_app.core import state as app_state


logger = logging.getLogger(__name__)


def load_model() -> None:
    from backend.model_app.core.settings import get_settings

    s = get_settings()
    mn = s.model_name
    logger.info("Loading %s with vLLM AWQ...", mn)
    app_state.llm = LLM(
        model=mn,
        quantization="awq",
        dtype="float16",
        gpu_memory_utilization=s.vllm_gpu_memory_utilization,
        max_model_len=s.vllm_max_model_len,
        max_num_seqs=s.vllm_max_num_seqs,
        trust_remote_code=True,
    )
    logger.info("vLLM model loaded successfully")


def _make_sampling_params(
    *,
    temperature: float,
    max_tokens: int,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
) -> SamplingParams:
    return SamplingParams(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        repetition_penalty=repetition_penalty,
    )


def _llm_chat_single(
    messages: list[dict[str, str]],
    *,
    temperature: float,
    max_tokens: int,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
) -> tuple[str, int, int]:
    llm = app_state.llm
    if llm is None:
        raise RuntimeError("vLLM is not loaded")
    sampling_params = _make_sampling_params(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        repetition_penalty=repetition_penalty,
    )
    outputs = llm.chat(messages=messages, sampling_params=sampling_params, use_tqdm=False)
    out = outputs[0]
    text = out.outputs[0].text.strip() if out.outputs else ""
    prompt_tokens = len(getattr(out, "prompt_token_ids", []) or [])
    completion_tokens = len(getattr(out.outputs[0], "token_ids", []) or []) if out.outputs else 0
    return text, prompt_tokens, completion_tokens


def _llm_chat_batch(
    messages_list: list[list[dict[str, str]]],
    *,
    temperature: float,
    max_tokens: int,
    top_p: float = 0.9,
    repetition_penalty: float = 1.1,
) -> tuple[list[str], list[tuple[int, int]]]:
    llm = app_state.llm
    if llm is None:
        raise RuntimeError("vLLM is not loaded")
    sampling_params = _make_sampling_params(
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        repetition_penalty=repetition_penalty,
    )
    outputs = llm.chat(messages=messages_list, sampling_params=sampling_params, use_tqdm=False)
    responses: list[str] = []
    token_stats: list[tuple[int, int]] = []
    for out in outputs:
        text = out.outputs[0].text.strip() if out.outputs else ""
        responses.append(text)
        prompt_tokens = len(getattr(out, "prompt_token_ids", []) or [])
        completion_tokens = len(getattr(out.outputs[0], "token_ids", []) or []) if out.outputs else 0
        token_stats.append((prompt_tokens, completion_tokens))
    return responses, token_stats
