"""Shared generation service layer."""

from __future__ import annotations

import asyncio
import json
import re
import time
import uuid

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.core.app import _emit_usage_metering, logger
from backend.model_app.core.state import STATS
from backend.model_app.prompts.aiml import build_aiml_prompt, calculate_aiml_token_limit
from backend.model_app.prompts.generation import (
    build_coding_prompt,
    build_sql_prompt,
    build_subjective_prompt,
    build_topics_prompt,
)
from backend.model_app.services.aiml import (
    generate_aiml_dataset,
    validate_aiml_output,
    validate_and_fix_aiml_response,
)
from backend.model_app.services.cache import (
    RESPONSE_CACHE,
    generate_cache_key,
    get_from_cache,
    save_to_cache,
)
from backend.model_app.services.jobs import (
    _job_store_set,
    _job_store_update,
)


def update_stats(endpoint: str) -> None:
    STATS["total_requests"] += 1
    if endpoint not in STATS["requests_by_endpoint"]:
        STATS["requests_by_endpoint"][endpoint] = 0
    STATS["requests_by_endpoint"][endpoint] += 1


def flatten_nested_fields(obj: dict) -> dict:
    flattened = {}
    for key, value in obj.items():
        if isinstance(value, dict):
            if len(value) == 1 and "description" in value:
                flattened[key] = value["description"]
            elif len(value) == 1 and "code" in value:
                flattened[key] = value["code"]
            elif len(value) == 1 and "text" in value:
                flattened[key] = value["text"]
            else:
                flattened[key] = value
        elif isinstance(value, list):
            flattened[key] = [
                item["description"] if isinstance(item, dict) and len(item) == 1 and "description" in item
                else item["text"] if isinstance(item, dict) and len(item) == 1 and "text" in item
                else item
                for item in value
            ]
        else:
            flattened[key] = value
    return flattened


def extract_json(text: str) -> dict:
    text = re.sub(r"```json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    text = text.strip()
    text = re.sub(r"(?<!\\)[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"(?<!\\)\n", " ", text)

    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    end = -1
    in_string = False
    i = start

    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == "\\":
                i += 2
                continue
            if ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        i += 1

    if end == -1:
        raise ValueError("Truncated JSON: no matching closing brace found.")

    json_str = text[start:end]

    try:
        obj = json.loads(json_str)
    except json.JSONDecodeError:
        cleaned = re.sub(r",\s*([}\]])", r"\1", json_str)
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError as e2:
            raise ValueError(f"JSON parse failed after cleanup: {str(e2)[:300]}")

    obj = flatten_nested_fields(obj)

    if "dataset" in obj:
        obj = validate_and_fix_aiml_response(obj)

    return obj


async def _run_generation_task(
    job_id: str,
    endpoint: str,
    request_data: dict,
    prompt_builder_func,
    max_tokens: int,
    num_q: int,
    use_cache: bool,
    usage_meta: dict | None,
    route: str = "",
):
    from backend.model_app.services.batching import add_to_batch_and_wait

    t0 = time.time()
    await _job_store_set(job_id, {"status": "processing", "result": None, "error": None})
    try:
        if endpoint == "topics":
            item_data = {k: v for k, v in request_data.items() if k not in ("num_questions",)}
            cache_key = generate_cache_key("topics", item_data)
            if use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    await _job_store_set(job_id, {"status": "complete", "result": cached, "error": None})
                    logger.info(f"Job {job_id[:8]} topics - cache hit")
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=usage_meta,
                        route=route,
                        cache_hit=True,
                        latency_ms=(time.time() - t0) * 1000,
                        status="success",
                    )
                    return
            result = await add_to_batch_and_wait("topics", item_data, cache_key, prompt_builder_func, max_tokens)
            result["cache_hit"] = False
            result["batched"] = True
            result["batch_size"] = num_q
            save_to_cache(cache_key, result)
            await _job_store_set(job_id, {"status": "complete", "result": result, "error": None})
            logger.info(f"Job {job_id[:8]} complete - topics generated")
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=usage_meta,
                route=route,
                cache_hit=False,
                latency_ms=(time.time() - t0) * 1000,
                status="success",
            )
            return

        all_items = []
        any_cache_hit = False
        total_time = 0.0

        for i in range(num_q):
            item_data = {k: v for k, v in request_data.items() if k not in ("num_questions",)}
            cache_key = generate_cache_key(endpoint, {**item_data, "question_index": i})

            if use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    any_cache_hit = True
                    all_items.append(cached)
                    continue

            result = await add_to_batch_and_wait(endpoint, item_data, cache_key, prompt_builder_func, max_tokens)
            save_to_cache(cache_key, result)
            total_time += result.get("generation_time_seconds", 0)
            all_items.append(result)

        key_map = {
            "mcq": "questions",
            "subjective": "questions",
            "coding": "coding_problems",
            "sql": "sql_problems",
            "aiml": "aiml_problems",
        }
        result_key = key_map.get(endpoint, "items")
        await _job_store_set(
            job_id,
            {
                "status": "complete",
                "result": {
                    result_key: all_items,
                    "generation_time_seconds": round(total_time, 3),
                    "cache_hit": any_cache_hit,
                    "batched": True,
                    "batch_size": num_q,
                },
                "error": None,
            },
        )
        logger.info(f"Job {job_id[:8]} complete - {num_q} {endpoint} item(s) generated")
        _emit_usage_metering(
            job_id=job_id,
            usage_meta=usage_meta,
            route=route,
            cache_hit=any_cache_hit,
            latency_ms=(time.time() - t0) * 1000,
            status="success",
        )
    except Exception as e:
        STATS["errors"] += 1
        logger.error(f"Job {job_id[:8]} failed: {e}")
        await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(e)})
        _emit_usage_metering(
            job_id=job_id,
            usage_meta=usage_meta,
            route=route,
            cache_hit=False,
            latency_ms=(time.time() - t0) * 1000,
            status="error",
            error_detail=str(e)[:500],
        )


async def generate_topics(body, http_request):
    update_stats("topics")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    item_data = {**data, "num_topics": num_q}
    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    cache_key = generate_cache_key("topics", item_data)
    if body.use_cache:
        cached = get_from_cache(cache_key)
        if cached:
            cached["cache_hit"] = True
            await _job_store_set(job_id, {"status": "complete", "result": cached, "error": None})
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-topics",
                cache_hit=True,
                latency_ms=0.0,
                status="success",
            )
            return {"job_id": job_id, "status": "complete"}

    asyncio.create_task(
        _run_generation_task(
            job_id,
            "topics",
            item_data,
            build_topics_prompt,
            3000,
            1,
            body.use_cache,
            usage_meta=um,
            route="generate-topics",
        )
    )
    return {"job_id": job_id, "status": "pending"}


async def generate_mcq(body, http_request):
    from backend.model_app.services.mcq import enqueue_and_wait

    update_stats("mcq")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _mcq_task():
        t0 = time.time()
        await _job_store_update(job_id, status="processing")
        try:
            all_questions = []
            any_cache_hit = False
            total_time = 0.0
            for i in range(num_q):
                item_data = {k: v for k, v in data.items() if k not in ("num_questions",)}
                if not item_data.get("request_id"):
                    item_data["request_id"] = str(uuid.uuid4())
                cache_key = generate_cache_key("mcq", {**item_data, "question_index": i})
                if body.use_cache and cache_key in RESPONSE_CACHE:
                    cached = dict(RESPONSE_CACHE[cache_key])
                    cached["cache_hit"] = True
                    any_cache_hit = True
                    all_questions.append(cached)
                    continue
                result = await enqueue_and_wait(item_data, cache_key)
                total_time += result.get("generation_time_seconds", 0)
                all_questions.append(result)
            await _job_store_set(
                job_id,
                {
                    "status": "complete",
                    "result": {
                        "questions": all_questions,
                        "generation_time_seconds": round(total_time, 3),
                        "cache_hit": any_cache_hit,
                        "batched": True,
                        "batch_size": num_q,
                    },
                    "error": None,
                },
            )
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-mcq",
                cache_hit=any_cache_hit,
                latency_ms=(time.time() - t0) * 1000,
                status="success",
            )
        except Exception as e:
            STATS["errors"] += 1
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(e)})
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-mcq",
                cache_hit=False,
                latency_ms=(time.time() - t0) * 1000,
                status="error",
                error_detail=str(e)[:500],
            )

    asyncio.create_task(_mcq_task())
    return {"job_id": job_id, "status": "pending"}


async def _schedule_generation_job(body, http_request, *, endpoint: str, prompt_builder, max_tokens: int):
    update_stats(endpoint)
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})
    asyncio.create_task(
        _run_generation_task(
            job_id,
            endpoint,
            data,
            prompt_builder,
            max_tokens,
            num_q,
            body.use_cache,
            usage_meta=um,
            route=f"generate-{endpoint}",
        )
    )
    return {"job_id": job_id, "status": "pending"}


async def generate_subjective(body, http_request):
    return await _schedule_generation_job(
        body,
        http_request,
        endpoint="subjective",
        prompt_builder=build_subjective_prompt,
        max_tokens=3000,
    )


async def generate_coding(body, http_request):
    return await _schedule_generation_job(
        body,
        http_request,
        endpoint="coding",
        prompt_builder=build_coding_prompt,
        max_tokens=4000,
    )


async def generate_sql(body, http_request):
    return await _schedule_generation_job(
        body,
        http_request,
        endpoint="sql",
        prompt_builder=build_sql_prompt,
        max_tokens=3500,
    )


async def generate_aiml(body, http_request):
    from backend.model_app.services.batching import add_to_batch_and_wait

    update_stats("aiml")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    job_id = str(uuid.uuid4())
    await _job_store_set(job_id, {"status": "pending", "result": None, "error": None})

    async def _aiml_task():
        t0 = time.time()
        await _job_store_update(job_id, status="processing")
        try:
            item_data = {k: v for k, v in data.items()}
            cache_key = generate_cache_key("aiml", item_data)

            if body.use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    await _job_store_set(
                        job_id,
                        {
                            "status": "complete",
                            "result": {
                                "aiml_problems": [cached],
                                "generation_time_seconds": 0,
                                "cache_hit": True,
                                "batched": False,
                                "batch_size": 1,
                            },
                            "error": None,
                        },
                    )
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml",
                        cache_hit=True,
                        latency_ms=(time.time() - t0) * 1000,
                        status="success",
                    )
                    return

            token_limit = calculate_aiml_token_limit(item_data)
            result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)

            difficulty = item_data.get("difficulty", "Medium").lower()
            num_rows = {"easy": 300, "medium": 400, "hard": 500}.get(difficulty, 400)

            try:
                dataset_schema = result.get("dataset", {})
                generated_rows = generate_aiml_dataset(dataset_schema, num_rows=num_rows)
                result["dataset"]["data"] = generated_rows
                result["dataset"]["size"] = f"{len(generated_rows)} samples"
                logger.info("Pass 2 complete: %s rows generated", len(generated_rows))
            except Exception as gen_err:
                logger.error("Pass 2 dataset generation failed: %s", gen_err)
                result["dataset"]["data"] = []
                result["dataset"]["size"] = "0 samples (generation failed)"

            target_type = result.get("dataset", {}).get("target_type", "")
            is_regression = "continuous" in target_type.lower()

            if not result.get("preprocessing_requirements") or result["preprocessing_requirements"] == [""]:
                feature_types = result.get("dataset", {}).get("feature_types", {})
                cat_feats = [f for f, t in feature_types.items() if "categorical" in t.lower()]
                num_feats = [f for f, t in feature_types.items() if "numerical" in t.lower()]
                steps = []
                if cat_feats:
                    steps.append(
                        f"Encode categorical features ({', '.join(cat_feats[:2])}) using LabelEncoder or OneHotEncoder."
                    )
                if num_feats:
                    steps.append(
                        f"Normalize numerical features ({', '.join(num_feats[:2])}) using MinMaxScaler or StandardScaler."
                    )
                steps.append("Split dataset 80/20 into training and test sets using train_test_split.")
                if not is_regression:
                    steps.append(
                        "Check for class imbalance - apply SMOTE or use class_weight='balanced' if needed."
                    )
                result["preprocessing_requirements"] = steps

            if not result.get("expectedApproach") or len(result.get("expectedApproach", "")) < 20:
                if is_regression:
                    result["expectedApproach"] = (
                        "Use Linear Regression as a baseline for interpretability. Also train Random Forest "
                        "Regressor which handles non-linear relationships well. Compare using RMSE and R^2 score."
                    )
                else:
                    result["expectedApproach"] = (
                        "Use Logistic Regression as a baseline for interpretability. Also train Random Forest "
                        "Classifier which handles non-linear feature interactions. Compare using F1-Score and ROC-AUC."
                    )

            if not result.get("evaluationCriteria") or result["evaluationCriteria"] == [""]:
                if is_regression:
                    result["evaluationCriteria"] = [
                        "Mean Absolute Error (MAE)",
                        "Root Mean Squared Error (RMSE)",
                        "R^2 Score",
                        "Mean Absolute Percentage Error (MAPE)",
                    ]
                else:
                    result["evaluationCriteria"] = [
                        "Accuracy",
                        "Precision",
                        "Recall",
                        "F1-Score",
                        "ROC-AUC Score",
                    ]

            result["dataset_strategy"] = "synthetic"

            topic_req = item_data.get("topic", "")
            concepts_req = item_data.get("concepts", [])
            difficulty_req = item_data.get("difficulty", "Medium")
            is_valid, issues = validate_aiml_output(
                result, topic_req, concepts_req, difficulty_req, matched_dataset=None
            )
            if not is_valid:
                logger.warning("Synthetic AIML output has quality issues - returning with warnings: %s", issues)
                result["validation_warnings"] = issues

            save_to_cache(cache_key, result)
            await _job_store_set(
                job_id,
                {
                    "status": "complete",
                    "result": {
                        "aiml_problems": [result],
                        "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3),
                        "cache_hit": False,
                        "batched": False,
                        "batch_size": 1,
                    },
                    "error": None,
                },
            )
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-aiml",
                cache_hit=False,
                latency_ms=(time.time() - t0) * 1000,
                status="success",
            )
        except Exception as e:
            STATS["errors"] += 1
            await _job_store_set(job_id, {"status": "failed", "result": None, "error": str(e)})
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-aiml",
                cache_hit=False,
                latency_ms=(time.time() - t0) * 1000,
                status="error",
                error_detail=str(e)[:500],
            )

    asyncio.create_task(_aiml_task())
    return {"job_id": job_id, "status": "pending"}


__all__ = [
    "_run_generation_task",
    "extract_json",
    "generate_aiml",
    "generate_coding",
    "generate_mcq",
    "generate_sql",
    "generate_subjective",
    "generate_topics",
    "update_stats",
]
