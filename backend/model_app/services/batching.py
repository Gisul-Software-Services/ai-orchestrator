from __future__ import annotations

import asyncio
import time
import uuid

import torch
from fastapi import HTTPException

from backend.model_app.core.app import _batch_size_max, _batch_timeout, logger
from backend.model_app.core.state import STATS, batch_locks, batch_queues, pending_results
from backend.model_app.services.cache import save_to_cache
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_batch


async def generate_batch_with_qwen(
    prompts: list[str], max_tokens: int = 2000, temperature: float = 0.7
):
    messages_list = []
    for prompt in prompts:
        messages_list.append(
            [
                {"role": "system", "content": "You are an expert assessment designer."},
                {"role": "user", "content": prompt},
            ]
        )

    start_time = time.time()
    responses, token_stats = _llm_chat_batch(
        messages_list,
        temperature=temperature,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=max_tokens,
    )

    try:
        input_tokens = int(sum(x[0] for x in token_stats))
        output_tokens = int(sum(x[1] for x in token_stats))
        from backend.model_app.billing.metering import current_token_counts

        current_token_counts.set(
            {
                "prompt_tokens": input_tokens,
                "completion_tokens": max(0, output_tokens),
                "total_tokens": max(0, input_tokens + output_tokens),
            }
        )
    except Exception:
        pass

    generation_time = time.time() - start_time

    STATS["total_generation_time"] += generation_time
    per_request_time = generation_time / max(1, len(responses))
    logger.info(
        f"BATCH: {len(prompts)} requests in {generation_time:.2f}s ({per_request_time:.2f}s each)"
    )
    return responses, generation_time, per_request_time


async def process_batch(endpoint: str, prompt_builder_func, max_tokens: int = 2000):
    queue = batch_queues[endpoint]
    if len(queue) == 0:
        return

    effective_batch_size = 1 if endpoint == "aiml" else _batch_size_max()

    endpoint_temperature = {
        "aiml": 0.6,
        "coding": 0.6,
        "sql": 0.65,
        "subjective": 0.7,
        "topics": 0.8,
        "mcq": 0.7,
    }.get(endpoint, 0.7)

    batch = []
    while len(batch) < effective_batch_size and len(queue) > 0:
        batch.append(queue.popleft())

    if len(batch) == 0:
        return

    batch_size = len(batch)
    logger.info(f"Processing batch of {batch_size} {endpoint} requests...")

    prompts, request_ids, cache_keys = [], [], []
    for item in batch:
        request_id, request_data, cache_key = item
        prompts.append(prompt_builder_func(request_data))
        request_ids.append(request_id)
        cache_keys.append(cache_key)

    try:
        responses, total_time, per_request_time = await generate_batch_with_qwen(
            prompts, max_tokens, endpoint_temperature
        )

        STATS["batches_processed"] += 1
        STATS["total_batched_requests"] += batch_size
        STATS["avg_batch_size"] = STATS["total_batched_requests"] / STATS["batches_processed"]

        for i, (request_id, cache_key, response) in enumerate(zip(request_ids, cache_keys, responses)):
            try:
                result = extract_json(response)
                result.update(
                    {
                        "generation_time_seconds": per_request_time,
                        "batched": True,
                        "batch_size": batch_size,
                        "cache_hit": False,
                    }
                )
                save_to_cache(cache_key, result)
                pending_results[request_id] = {"success": True, "data": result}
            except Exception as e:
                logger.error(f"Error processing batch item {i}: {e}. Retrying...")
                try:
                    retry_prompt = prompt_builder_func(batch[i][1])
                    retry_responses, _, _ = await generate_batch_with_qwen(
                        [retry_prompt], max_tokens, endpoint_temperature
                    )
                    retry_result = extract_json(retry_responses[0])
                    retry_result.update(
                        {
                            "generation_time_seconds": per_request_time,
                            "batched": True,
                            "batch_size": batch_size,
                            "cache_hit": False,
                        }
                    )
                    save_to_cache(cache_key, retry_result)
                    pending_results[request_id] = {"success": True, "data": retry_result}
                    logger.info(f"Retry successful for batch item {i}")
                except Exception as retry_error:
                    logger.error(f"Retry failed for batch item {i}: {retry_error}")
                    pending_results[request_id] = {
                        "success": False,
                        "error": f"Generation failed: {str(retry_error)}",
                    }
    except torch.cuda.OutOfMemoryError:
        logger.error(
            "CUDA OOM in batch processing - freeing cache, marking all items failed for retry"
        )
        torch.cuda.empty_cache()
        for request_id in request_ids:
            pending_results[request_id] = {
                "success": False,
                "error": "GPU ran out of memory. Please try again with fewer simultaneous requests.",
            }
    except Exception as e:
        logger.error(f"Batch processing error: {e}")
        for request_id in request_ids:
            pending_results[request_id] = {"success": False, "error": str(e)}


async def add_to_batch_and_wait(endpoint, request_data, cache_key, prompt_builder_func, max_tokens=2000):
    request_id = str(uuid.uuid4())
    batch_queues[endpoint].append((request_id, request_data, cache_key))
    logger.info(f"Added to {endpoint} queue. Size: {len(batch_queues[endpoint])}")

    if len(batch_queues[endpoint]) >= _batch_size_max():
        async with batch_locks[endpoint]:
            await process_batch(endpoint, prompt_builder_func, max_tokens)
    else:
        await asyncio.sleep(_batch_timeout())
        if request_id not in pending_results:
            async with batch_locks[endpoint]:
                if request_id not in pending_results:
                    await process_batch(endpoint, prompt_builder_func, max_tokens)

    for _ in range(600):
        if request_id in pending_results:
            result = pending_results.pop(request_id)
            if result["success"]:
                return result["data"]
            raise HTTPException(status_code=500, detail=result["error"])
        await asyncio.sleep(0.1)

    raise HTTPException(status_code=504, detail="Request timeout")
