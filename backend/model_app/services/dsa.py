from __future__ import annotations

import json
import logging
import os as _os
import random
import time
import uuid

import numpy as _np
from fastapi import HTTPException

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.core.app import _emit_usage_metering, logger
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single


def _classify_testcase(raw_input: str) -> str:
    import re

    numbers = re.findall(r"-?\d+", raw_input)
    if numbers:
        vals = [int(n) for n in numbers]
        if any(abs(v) >= 1000000 for v in vals):
            return "edge"
        if any(v < 0 for v in vals):
            return "edge"

    arrays = re.findall(r"\[([^\[\]]*)\]", raw_input)
    for arr in arrays:
        elements = [e.strip() for e in arr.split(",") if e.strip()]
        if len(elements) == 0:
            return "edge"
        if len(elements) == 1:
            return "edge"
        if len(elements) >= 8:
            return "edge"
        if len(set(elements)) == 1 and len(elements) > 1:
            return "edge"

    if '""' in raw_input or "''" in raw_input:
        return "edge"

    strings = re.findall(r'"([^"]*)"', raw_input)
    for s in strings:
        if len(s) >= 10:
            return "edge"

    return "simple"


def _parse_input_output(input_output: list) -> tuple:
    all_cases = []

    for item in input_output:
        raw_input = (item.get("input") or "").strip()
        raw_output = (item.get("output") or "").strip()

        if not raw_input or not raw_output:
            continue

        try:
            expected_output = json.loads(raw_output)
        except Exception:
            expected_output = raw_output

        case_type = _classify_testcase(raw_input)
        all_cases.append(
            {
                "input_raw": raw_input,
                "expected_output": expected_output,
                "case_type": case_type,
            }
        )

    simple_cases = [c for c in all_cases if c["case_type"] == "simple"]
    edge_cases = [c for c in all_cases if c["case_type"] == "edge"]

    if len(simple_cases) < 2:
        simple_cases = all_cases[:4]
        edge_cases = all_cases[4:]

    public_testcases = []
    for c in simple_cases[:4]:
        public_testcases.append(
            {
                "input_raw": c["input_raw"],
                "expected_output": c["expected_output"],
                "is_hidden": False,
                "case_type": "simple",
            }
        )

    hidden_pool = edge_cases + [c for c in simple_cases[4:]]
    hidden_testcases = []
    for c in hidden_pool[:8]:
        hidden_testcases.append(
            {
                "input_raw": c["input_raw"],
                "expected_output": c["expected_output"],
                "is_hidden": True,
                "case_type": "edge",
            }
        )

    return public_testcases, hidden_testcases


def _build_starter_prompt(problem: dict) -> str:
    title = problem.get("title", "")
    difficulty = problem.get("difficulty", "Medium")
    topics = ", ".join(problem.get("tags", problem.get("topics", [])))
    description = problem.get("problem_description", problem.get("description", ""))[:400]
    starter_code = problem.get("starter_code", "")
    entry_point = problem.get("entry_point", "")

    fn_hint = ""
    if entry_point:
        fn_hint = entry_point.split(".")[-1].strip() if "." in entry_point else entry_point

    return f"""You are an expert software engineer.

Given this coding problem:
Title: {title}
Difficulty: {difficulty}
Topics: {topics}
Description: {description}

Python starter code:
{starter_code}

Function name: {fn_hint}

Generate ONLY this JSON (no extra text):
{{
  "function_signature": {{
    "name": "{fn_hint}",
    "parameters": [
      {{"name": "paramName1", "type": "List[int]"}},
      {{"name": "paramName2", "type": "int"}}
    ],
    "return_type": "List[int]"
  }},
  "starter_code": {{
    "python":     "def {fn_hint}(param1: List[int], param2: int) -> List[int]:\\n    pass",
    "java":       "class Solution {{\\n    public int[] {fn_hint}(int[] param1, int param2) {{\\n        \\n    }}\\n}}",
    "javascript": "var {fn_hint} = function(param1, param2) {{\\n    \\n}};",
    "typescript": "function {fn_hint}(param1: number[], param2: number): number[] {{\\n    \\n}};",
    "kotlin":     "class Solution {{\\n    fun {fn_hint}(param1: IntArray, param2: Int): IntArray {{\\n        \\n    }}\\n}}",
    "go":         "func {fn_hint}(param1 []int, param2 int) []int {{\\n    \\n}}",
    "rust":       "impl Solution {{\\n    pub fn {fn_hint}(param1: Vec<i32>, param2: i32) -> Vec<i32> {{\\n        \\n    }}\\n}}",
    "cpp":        "#include <bits/stdc++.h>\\nusing namespace std;\\nclass Solution {{\\npublic:\\n    vector<int> {fn_hint}(vector<int>& param1, int param2) {{\\n        \\n    }}\\n}};",
    "csharp":     "public class Solution {{\\n    public int[] {fn_hint}(int[] param1, int param2) {{\\n        \\n    }}\\n}}",
    "c":          "int* {fn_hint}(int* param1, int param1Size, int param2, int* returnSize) {{\\n    \\n}}"
  }}
}}

RULES:
1. function_signature: use EXACT function name from entry point above.
2. starter_code: use EXACT function name for ALL 10 languages.
3. Return ONLY valid JSON. No markdown, no explanation.

Generate now:"""


def _dsa_enriched_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().dsa_enriched_path)


def _dsa_faiss_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().dsa_faiss_path)


def _dsa_metadata_path() -> str:
    from backend.model_app.core.settings import get_settings

    return str(get_settings().dsa_metadata_path)


_dsa_enriched_cache = None
_dsa_faiss_index = None
_dsa_metadata_cache = None
_dsa_embed_model = None


def _load_dsa_enriched():
    global _dsa_enriched_cache
    if _dsa_enriched_cache is None:
        p = _dsa_enriched_path()
        if not _os.path.exists(p):
            raise FileNotFoundError(f"dsa_enriched.json not found at {p}")
        with open(p, encoding="utf-8") as f:
            _dsa_enriched_cache = json.load(f)
        logger.info("Loaded %s problems from dsa_enriched.json", len(_dsa_enriched_cache))
    return _dsa_enriched_cache


def _load_faiss_index():
    global _dsa_faiss_index, _dsa_metadata_cache, _dsa_embed_model
    if _dsa_faiss_index is None:
        if not _os.path.exists(_dsa_faiss_path()):
            logger.warning("FAISS index not found - falling back to keyword matching")
            return False
        try:
            import faiss
            from sentence_transformers import SentenceTransformer

            logger.info("Loading FAISS index...")
            _dsa_faiss_index = faiss.read_index(_dsa_faiss_path())

            logger.info("Loading metadata...")
            with open(_dsa_metadata_path(), encoding="utf-8") as f:
                _dsa_metadata_cache = json.load(f)

            logger.info("Loading embedding model...")
            _dsa_embed_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("FAISS ready: %s vectors", _dsa_faiss_index.ntotal)
            return True
        except Exception as e:
            logger.warning("FAISS load failed: %s - falling back to keyword matching", e)
            return False
    return True


def _faiss_search(query: str, difficulty: str, top_k: int = 20) -> list:
    problems = _load_dsa_enriched()
    query_vec = _dsa_embed_model.encode([query], convert_to_numpy=True, normalize_embeddings=True).astype(_np.float32)
    scores, indices = _dsa_faiss_index.search(query_vec, top_k * 3)

    matched = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(_dsa_metadata_cache):
            continue
        meta = _dsa_metadata_cache[idx]
        if meta.get("difficulty", "").lower() != difficulty.lower():
            continue
        if idx < len(problems):
            matched.append(problems[idx])
        if len(matched) >= top_k:
            break
    return matched


def _keyword_filter(problems: list, difficulty: str, topic: str, concepts: list) -> list:
    difficulty_lower = difficulty.lower()
    keywords = [topic.lower()] + [c.lower() for c in concepts]

    matched = []
    for p in problems:
        if p.get("difficulty", "").lower() != difficulty_lower:
            continue
        searchable = " ".join(
            [
                p.get("title", ""),
                p.get("task_id", ""),
                p.get("problem_description", ""),
                p.get("description", ""),
                " ".join(p.get("tags", [])),
                " ".join(p.get("topics", [])),
            ]
        ).lower()
        if any(kw in searchable for kw in keywords):
            matched.append(p)
    return matched


def _build_reword_prompt(problem: dict) -> str:
    title = problem.get("title", problem.get("task_id", ""))
    description = problem.get("problem_description", problem.get("description", ""))[:600]

    return f"""You are a technical problem designer.

Below is a coding problem. Your job is to REWORD the problem statement and title ONLY.

STRICT RULES:
- Keep the EXACT same algorithmic logic and solution approach.
- Keep the EXACT same input/output format.
- Change ONLY the real-world story/context.
- Return ONLY valid JSON.

ORIGINAL TITLE: {title}

ORIGINAL DESCRIPTION:
{description}

Return this exact JSON structure:
{{
  "title": "Reworded title here",
  "description": "Reworded full problem description here - same logic, different story/context"
}}

Generate now:"""


async def enrich_dsa(http_request, problem: dict):
    um = bind_usage_meta_from_request(http_request)
    rid = str(uuid.uuid4())
    t0 = time.perf_counter()
    title = problem.get("title", problem.get("task_id", ""))
    input_output = problem.get("input_output", [])

    logger.info("DSA enrich v3: %s", title)

    public_testcases, hidden_testcases = _parse_input_output(input_output)
    if not public_testcases and not hidden_testcases:
        raise HTTPException(status_code=500, detail="No input_output data found - cannot generate test cases")

    prompt = _build_starter_prompt(problem)

    try:
        messages = [
            {"role": "system", "content": "You are an expert software engineer. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        decoded, in_tok, out_tok = _llm_chat_single(
            messages,
            temperature=0.2,
            top_p=0.9,
            repetition_penalty=1.1,
            max_tokens=2000,
        )
        try:
            from backend.model_app.billing.metering import current_token_counts

            current_token_counts.set(
                {
                    "prompt_tokens": max(0, in_tok),
                    "completion_tokens": max(0, out_tok),
                    "total_tokens": max(0, in_tok + out_tok),
                }
            )
        except Exception:
            pass
        result = extract_json(decoded)
    except Exception as e:
        logger.error("Qwen starter generation failed for '%s': %s", title, e)
        raise HTTPException(status_code=500, detail=str(e))

    for field in ["function_signature", "starter_code"]:
        if field not in result:
            raise HTTPException(status_code=500, detail=f"Missing field: {field}")

    logger.info(
        "Enrichment done: %s | public=%s, hidden=%s, langs=%s",
        title,
        len(public_testcases),
        len(hidden_testcases),
        len(result.get("starter_code", {})),
    )

    _emit_usage_metering(
        job_id=rid,
        usage_meta=um,
        route="enrich-dsa",
        cache_hit=False,
        latency_ms=(time.perf_counter() - t0) * 1000,
        status="success",
    )

    return {
        "pipeline": "dataset_driven",
        "test_case_source": "leetcode_dataset",
        "function_signature": result["function_signature"],
        "public_testcases": public_testcases,
        "hidden_testcases": hidden_testcases,
        "starter_code": result["starter_code"],
    }


async def generate_dsa_question(body, http_request):
    um = bind_usage_meta_from_request(http_request)
    rid = str(uuid.uuid4())
    t0 = time.perf_counter()
    request = body
    problems = _load_dsa_enriched()
    query = f"{request.topic} {' '.join(request.concepts)} {request.difficulty}"
    faiss_available = _load_faiss_index()

    if faiss_available:
        logger.info("Using FAISS search for: %s", query)
        matched = _faiss_search(query, request.difficulty, top_k=20)
        search_method = "faiss"
    else:
        logger.info("Using keyword search for: %s", query)
        matched = _keyword_filter(problems, request.difficulty, request.topic, request.concepts)
        search_method = "keyword"

    if not matched:
        logger.warning("No match found - falling back to difficulty only filter")
        matched = [p for p in problems if p.get("difficulty", "").lower() == request.difficulty.lower()]
        search_method = "difficulty_only"

    if not matched:
        raise HTTPException(status_code=404, detail=f"No problems found for difficulty='{request.difficulty}'")

    selected = random.choice(matched)
    logger.info(
        "Selected: '%s' (%s) via %s",
        selected.get("title", selected.get("task_id")),
        selected.get("difficulty"),
        search_method,
    )

    prompt = _build_reword_prompt(selected)

    try:
        messages = [
            {"role": "system", "content": "You are a technical problem designer. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ]
        decoded, in_tok, out_tok = _llm_chat_single(
            messages,
            temperature=0.75,
            top_p=0.9,
            repetition_penalty=1.1,
            max_tokens=1500,
        )
        try:
            from backend.model_app.billing.metering import current_token_counts

            current_token_counts.set(
                {
                    "prompt_tokens": max(0, in_tok),
                    "completion_tokens": max(0, out_tok),
                    "total_tokens": max(0, in_tok + out_tok),
                }
            )
        except Exception:
            pass
        reworded = extract_json(decoded)
    except Exception as e:
        logger.error("Qwen reword failed: %s - returning original wording", e)
        reworded = {
            "title": selected.get("title", selected.get("task_id", "")),
            "description": selected.get("problem_description", selected.get("description", "")),
        }

    all_starter_code = selected.get("starter_code_langs", selected.get("starter_code", {}))
    if request.languages:
        filtered_starter_code = {
            lang: code
            for lang, code in all_starter_code.items()
            if lang.lower() in [l.lower() for l in request.languages]
        }
    else:
        filtered_starter_code = all_starter_code

    _emit_usage_metering(
        job_id=rid,
        usage_meta=um,
        route="generate-dsa-question",
        cache_hit=False,
        latency_ms=(time.perf_counter() - t0) * 1000,
        status="success",
    )

    return {
        "original_title": selected.get("title", selected.get("task_id", "")),
        "title": reworded.get("title", selected.get("title", "")),
        "description": reworded.get("description", selected.get("problem_description", "")),
        "function_signature": selected.get("function_signature", {}),
        "public_testcases": selected.get("public_testcases", []),
        "hidden_testcases": selected.get("hidden_testcases", []),
        "starter_code": filtered_starter_code,
        "difficulty": selected.get("difficulty", request.difficulty),
        "tags": selected.get("tags", selected.get("topics", [])),
        "examples": selected.get("examples", []),
        "example_images": selected.get("example_images", []),
        "search_method": search_method,
        "ai_generated": True,
        "reworded": True,
    }
