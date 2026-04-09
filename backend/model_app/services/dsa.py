from __future__ import annotations

import ast
import json
import logging
import os as _os
import random
import re
import time
import uuid
from typing import Any

import numpy as _np
from fastapi import HTTPException

from backend.model_app.billing.metering import bind_usage_meta_from_request
from backend.model_app.core.app import _emit_usage_metering, logger
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_single


_UNSUPPORTED_RESTRICTED_PATH_PHRASES = (
    "threshold",
    "distance does not exceed",
)

_INVALID_EXPECTED_OUTPUT_PATTERNS = (
    re.compile(r"^\s*error\s*:", re.IGNORECASE),
    re.compile(r"^\s*exception\b", re.IGNORECASE),
    re.compile(r"^\s*traceback\b", re.IGNORECASE),
)

_INVALID_EXPECTED_OUTPUT_SUBSTRINGS = (
    "list assignment index out of range",
    "index out of range",
    "out of bounds",
    "execution timed out",
)


def _problem_title(problem: dict) -> str:
    return str(problem.get("title", problem.get("task_id", "")) or "")


def _problem_description(problem: dict) -> str:
    return str(problem.get("problem_description", problem.get("description", "")) or "")


def _is_restricted_path_problem(problem: dict) -> bool:
    title_lower = _problem_title(problem).lower()
    desc_lower = _problem_description(problem).lower()
    return "restricted path" in title_lower or (
        "restricted path" in desc_lower and "distancetolastnode" in desc_lower
    )


def _restricted_path_guardrails() -> str:
    return """
RESTRICTED-PATH DEFINITION LOCK:
- A restricted path is one where distToN(zi) > distToN(zi+1) for all adjacent nodes.
- Preserve the original shortest-distance-to-node-n semantics.
- Do NOT replace this with threshold-based wording or any "distance does not exceed" rule.
- Preserve the core semantics of the original title/problem.
"""


def _get_python_starter_code(problem: dict) -> str:
    starter_code_langs = problem.get("starter_code_langs")
    if isinstance(starter_code_langs, dict):
        py = starter_code_langs.get("python")
        if isinstance(py, str) and py.strip():
            return py

    starter_code = problem.get("starter_code")
    if isinstance(starter_code, dict):
        py = starter_code.get("python")
        if isinstance(py, str) and py.strip():
            return py
    elif isinstance(starter_code, str) and starter_code.strip():
        return starter_code

    return ""


def _extract_signature_from_python_starter(problem: dict) -> dict | None:
    code = _get_python_starter_code(problem)
    if not code:
        return None

    match = re.search(
        r"def\s+(?P<name>\w+)\s*\((?P<params>[^)]*)\)\s*(?:->\s*(?P<ret>[^:\n]+))?:",
        code,
    )
    if not match:
        return None

    raw_params = [p.strip() for p in match.group("params").split(",") if p.strip()]
    parameters: list[dict[str, str]] = []
    for raw_param in raw_params:
        if raw_param == "self":
            continue
        if ":" in raw_param:
            name, raw_type = raw_param.split(":", 1)
            parameters.append(
                {
                    "name": name.strip(),
                    "type": raw_type.strip(),
                }
            )
        else:
            parameters.append({"name": raw_param.strip(), "type": "Any"})

    return {
        "name": match.group("name").strip(),
        "parameters": parameters,
        "return_type": (match.group("ret") or "Any").strip(),
    }


def _split_top_level_commas(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    in_string = False
    string_char = ""
    i = 0

    while i < len(text):
        ch = text[i]
        if in_string:
            buf.append(ch)
            if ch == "\\" and i + 1 < len(text):
                i += 1
                buf.append(text[i])
            elif ch == string_char:
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                string_char = ch
                buf.append(ch)
            elif ch in "([{":
                depth += 1
                buf.append(ch)
            elif ch in ")]}":
                depth = max(0, depth - 1)
                buf.append(ch)
            elif ch == "," and depth == 0:
                part = "".join(buf).strip()
                if part:
                    parts.append(part)
                buf = []
            else:
                buf.append(ch)
        i += 1

    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def _parse_named_input_raw(raw_input: str) -> dict[str, Any] | None:
    if "=" not in raw_input:
        return None

    parsed: dict[str, Any] = {}
    for part in _split_top_level_commas(raw_input):
        if "=" not in part:
            return None
        name, raw_value = part.split("=", 1)
        key = name.strip()
        value_text = raw_value.strip()
        if not key:
            return None
        try:
            parsed[key] = ast.literal_eval(value_text)
        except Exception:
            return None
    return parsed or None


def _looks_like_edge_list(value: Any) -> bool:
    if not isinstance(value, list) or not value:
        return False
    for edge in value:
        if not isinstance(edge, (list, tuple)) or len(edge) not in (2, 3):
            return False
        if any(not isinstance(x, int) for x in edge):
            return False
    return True


def _allows_self_loops(problem: dict) -> bool:
    desc_lower = _problem_description(problem).lower()
    if "ui != vi" in desc_lower or "no self-loop" in desc_lower or "no self loop" in desc_lower:
        return False
    return "self-loop" in desc_lower or "self loop" in desc_lower


def _normalize_graph_testcases(problem: dict, cases: list[dict], *, label: str) -> list[dict]:
    allow_self_loops = _allows_self_loops(problem)
    normalized: list[dict] = []

    for case in cases:
        raw_input = str(case.get("input_raw", "") or "").strip()
        parsed = _parse_named_input_raw(raw_input)
        if not parsed:
            normalized.append(case)
            continue

        edges = parsed.get("edges")
        if not _looks_like_edge_list(edges):
            normalized.append(case)
            continue

        malformed = False
        has_self_loop = False
        for edge in edges:
            if len(edge) not in (2, 3):
                malformed = True
                break
            if edge[0] == edge[1]:
                has_self_loop = True

        if malformed:
            logger.warning("Dropping malformed %s testcase for '%s': %s", label, _problem_title(problem), raw_input)
            continue
        if has_self_loop and not allow_self_loops:
            logger.warning("Dropping self-loop %s testcase for '%s': %s", label, _problem_title(problem), raw_input)
            continue

        normalized.append(case)

    return normalized


def _is_invalid_expected_output(value: Any) -> bool:
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return True
        if any(pattern.search(text) for pattern in _INVALID_EXPECTED_OUTPUT_PATTERNS):
            return True
        lowered = text.lower()
        if any(token in lowered for token in _INVALID_EXPECTED_OUTPUT_SUBSTRINGS):
            return True
    return False


def _sanitize_expected_output_testcases(problem: dict, cases: list[dict], *, label: str) -> list[dict]:
    sanitized: list[dict] = []
    for case in cases:
        expected_output = case.get("expected_output")
        if _is_invalid_expected_output(expected_output):
            logger.warning(
                "Dropping testcase with invalid expected_output for '%s' (%s): %r",
                _problem_title(problem),
                label,
                expected_output,
            )
            continue
        sanitized.append(case)
    return sanitized


def _normalize_function_signature(
    problem: dict,
    signature: dict,
    public_testcases: list[dict],
    hidden_testcases: list[dict],
) -> dict:
    normalized = dict(signature or {})
    starter_signature = _extract_signature_from_python_starter(problem)
    if starter_signature:
        normalized = starter_signature

    entry_point = str(problem.get("entry_point", "") or "")
    fn_hint = entry_point.split(".")[-1].strip() if entry_point else ""
    if fn_hint:
        normalized["name"] = fn_hint

    parameters = normalized.get("parameters")
    if not isinstance(parameters, list):
        normalized["parameters"] = []
        parameters = normalized["parameters"]

    parsed_case = None
    for case in public_testcases + hidden_testcases:
        parsed_case = _parse_named_input_raw(str(case.get("input_raw", "") or ""))
        if parsed_case:
            break

    if parsed_case and parameters:
        order = list(parsed_case.keys())
        param_map = {
            str(param.get("name")): param
            for param in parameters
            if isinstance(param, dict) and param.get("name")
        }
        if param_map and set(order) == set(param_map.keys()):
            normalized["parameters"] = [param_map[name] for name in order]

    return normalized


def _normalize_reworded_problem(problem: dict, reworded: dict) -> dict:
    original_title = _problem_title(problem)
    original_description = _problem_description(problem)

    title = str(reworded.get("title", "") or "").strip() or original_title
    description = str(reworded.get("description", "") or "").strip() or original_description

    if _is_restricted_path_problem(problem):
        description_lower = description.lower()
        unsupported_phrase = next(
            (phrase for phrase in _UNSUPPORTED_RESTRICTED_PATH_PHRASES if phrase in description_lower),
            None,
        )
        has_definition_lock = (
            "restricted path" in description_lower
            and (
                "distancetolastnode(zi) > distancetolastnode(zi+1)" in description_lower
                or "distton(zi) > distton(zi+1)" in description_lower
            )
        )
        if unsupported_phrase or not has_definition_lock:
            logger.warning(
                "Restricted-path reword failed validation for '%s'; falling back to source wording",
                original_title,
            )
            title = original_title
            description = original_description

    return {"title": title, "description": description}


def _normalize_dsa_payload(problem: dict, payload: dict, *, validate_reworded_text: bool) -> dict:
    normalized = dict(payload)
    public_testcases = _normalize_graph_testcases(
        problem,
        list(normalized.get("public_testcases", []) or []),
        label="public",
    )
    public_testcases = _sanitize_expected_output_testcases(problem, public_testcases, label="public")
    hidden_testcases = _normalize_graph_testcases(
        problem,
        list(normalized.get("hidden_testcases", []) or []),
        label="hidden",
    )
    hidden_testcases = _sanitize_expected_output_testcases(problem, hidden_testcases, label="hidden")
    if not public_testcases and not hidden_testcases:
        raise HTTPException(status_code=500, detail="No valid DSA testcases remain after validation")

    normalized["public_testcases"] = public_testcases
    normalized["hidden_testcases"] = hidden_testcases

    if "function_signature" in normalized:
        normalized["function_signature"] = _normalize_function_signature(
            problem,
            normalized.get("function_signature", {}) or {},
            public_testcases,
            hidden_testcases,
        )

    if validate_reworded_text:
        normalized.update(_normalize_reworded_problem(problem, normalized))

    return normalized


def _classify_testcase(raw_input: str) -> str:
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

        if _is_invalid_expected_output(expected_output):
            logger.warning("Skipping dataset testcase with invalid expected_output: %r", expected_output)
            continue

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
   Extract parameter names + types from the Python starter code in the EXACT same order.
2. starter_code: use EXACT function name for ALL 10 languages.
3. If the canonical parameters are (n, edges), keep them in that exact order everywhere.
   Do NOT swap to (edges, n).
4. Return ONLY valid JSON. No markdown, no explanation.

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
    extra_rules = _restricted_path_guardrails() if _is_restricted_path_problem(problem) else ""

    return f"""You are a technical problem designer.

Below is a coding problem. Your job is to REWORD the problem statement and title ONLY.

STRICT RULES:
- Keep the EXACT same algorithmic logic and solution approach.
- Keep the EXACT same input/output format.
- Change ONLY the real-world story/context.
- Preserve the core semantics of the original title/problem.
- Do NOT introduce any new constraints unless they are explicitly present in the source.
{extra_rules}
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

    normalized_payload = _normalize_dsa_payload(
        {**problem, "starter_code": result.get("starter_code", {})},
        {
            "function_signature": result["function_signature"],
            "public_testcases": public_testcases,
            "hidden_testcases": hidden_testcases,
        },
        validate_reworded_text=False,
    )

    logger.info(
        "Enrichment done: %s | public=%s, hidden=%s, langs=%s",
        title,
        len(normalized_payload["public_testcases"]),
        len(normalized_payload["hidden_testcases"]),
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
        "function_signature": normalized_payload["function_signature"],
        "public_testcases": normalized_payload["public_testcases"],
        "hidden_testcases": normalized_payload["hidden_testcases"],
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

    response_payload = _normalize_dsa_payload(
        selected,
        {
            "title": reworded.get("title", selected.get("title", "")),
            "description": reworded.get("description", selected.get("problem_description", "")),
            "function_signature": selected.get("function_signature", {}),
            "public_testcases": selected.get("public_testcases", []),
            "hidden_testcases": selected.get("hidden_testcases", []),
        },
        validate_reworded_text=True,
    )

    return {
        "original_title": selected.get("title", selected.get("task_id", "")),
        "title": response_payload["title"],
        "description": response_payload["description"],
        "function_signature": response_payload["function_signature"],
        "public_testcases": response_payload["public_testcases"],
        "hidden_testcases": response_payload["hidden_testcases"],
        "starter_code": filtered_starter_code,
        "difficulty": selected.get("difficulty", request.difficulty),
        "tags": selected.get("tags", selected.get("topics", [])),
        "examples": selected.get("examples", []),
        "example_images": selected.get("example_images", []),
        "search_method": search_method,
        "ai_generated": True,
        "reworded": True,
    }
