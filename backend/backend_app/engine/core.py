"""
Qwen Question Generation API - PRODUCTION HARDENED VERSION v9.0
===============================================================
✅ ALL 6 endpoints working
✅ Deterministic-first MCQ pipeline for code/output-prediction topics
✅ LLM generates context only for code MCQs — system executes and decides correctness
✅ Ambiguity detector rejects vague/opinion-based questions
✅ Official API protection prevents valid APIs from being wrongly marked wrong
✅ MCQ with advanced verification & safety checks (conceptual topics)
✅ Confidence-based code detection (avoids false positives)
✅ Structured deterministic validation result
✅ Robust expression extraction with bracket counting
✅ Hardened sandbox execution (no env vars, blocked dangerous builtins)
✅ Fixed retry logic (no UnboundLocalError, no cascading failures)
✅ Cleaner JSON extraction (brace-counting, no silent corruption)
✅ Prefer skip over false rejection
✅ Auto-correct only when exactly 1 option matches

New in v7.0 — Deterministic-first MCQ architecture:
  ARCH — Two MCQ sub-pipelines, routed by JSON shape:
         • Code/output-prediction topics (Python, slicing, etc.):
           build_mcq_context_prompt() → LLM generates context only (no correct answer)
           → _run_deterministic_mcq_pipeline() → safe_execute() → build_deterministic_mcq()
           → correct answer computed by Python interpreter, not LLM
           → NO LLM verifier needed for these
         • Conceptual/framework topics (React, Next.js, SQL, etc.):
           build_mcq_prompt() → LLM generates full MCQ
           → existing LLM-verified pipeline unchanged

  ADD  — build_mcq_context_prompt(): generates setup_code, expression,
          distractors, explanation_template only. Never asks LLM for correct answer.

  ADD  — build_deterministic_mcq(): executes expression via safe_execute(),
          filters accidental correct-answer distractors, shuffles options,
          fills explanation template with computed output. Correctness is 100% deterministic.

  ADD  — _run_deterministic_mcq_pipeline(): validates context fields,
          calls build_deterministic_mcq(), runs structural checks.
          No LLM verifier call — Python interpreter is the verifier.

  MOD  — build_mcq_prompt(): routes code topics to build_mcq_context_prompt()
          via _CODE_TOPIC_KEYWORDS list. Non-code topics use existing domain-hint prompt.

  MOD  — _run_mcq_pipeline(): detects routing by JSON shape.
          If "expression" + "distractors" present → deterministic pipeline.
          Otherwise → existing LLM-verified pipeline.

New in v6.1:
  FIX 7 — detect_ambiguity(): rejects MCQs with vague opinion-based phrasing.
  FIX 8 — protect_official_api_logic(): context-aware API protection.
  FIX 9 — build_mcq_prompt() ANTI-AMBIGUITY RULES block.

Fixes applied in v6.0:
  FIX 1 — verify_mcq_with_llm(): checks for rejected:true from verifier.
  FIX 2 — safe_execute(): minimal PATH env instead of env={}.
  FIX 3 — _BLOCKED_CODE_PATTERNS: added from-import pattern.
  FIX 4 — explanation_mismatch: changed to skip instead of reject.
  FIX 5 — extract_json(): AIML validation gated behind dataset key check.
  FIX 6 — build_mcq_prompt(): domain-aware rules for 12+ tech domains.

Bugs fixed in v5.0:
  BUG 1 — process_mcq_batch(): logger.info between try/except → SyntaxError
  BUG 2 — enqueue_and_wait(): 7-space indent broke poll loop → 504 timeout
  BUG 3 — extract_expression(): missing \\s* after [:\\-]? broke regex
  BUG 4 — pending_results stored raw RuntimeError → 500 on enqueue_and_wait

Routing fix in v7.1:
  FIX ROUTING — _CODE_TOPIC_KEYWORDS narrowed to execution-specific signals only.
    Removed: 'python', 'decorator', 'closure', 'recursion', 'scope', 'lambda',
             'asyncio', 'generator', 'dictionary', 'mutable default',
             'list comprehension' (bare, without 'output' qualifier).
    These are concept topics and must route to the conceptual pipeline.
    Deterministic pipeline now triggers ONLY on slicing, indexing, output-prediction,
    and explicit code-execution topic phrasings.

Endpoints:
1. /api/v1/generate-topics
2. /api/v1/generate-mcq (with verification + deterministic validation)
3. /api/v1/generate-subjective
4. /api/v1/generate-coding
5. /api/v1/generate-sql
6. /api/v1/generate-aiml
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any, Optional, Tuple
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import os
import json
import re
import time
import ast
import subprocess
from datetime import datetime, timezone
import logging
import hashlib
from cachetools import TTLCache
import asyncio
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from starlette.requests import Request

from backend_app.billing.metering import bind_usage_meta_from_request, schedule_usage_emit
import uuid
import random
import numpy as np

# ----------------------------------------------------------------------------
# LOGGING
# ----------------------------------------------------------------------------
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ----------------------------------------------------------------------------
# BATCH CONFIG (reads from settings — see backend_app.core.settings)
# ----------------------------------------------------------------------------


def _batch_size_max() -> int:
    from backend_app.core.settings import get_settings

    return max(1, get_settings().batch_size_max)


def _batch_timeout() -> float:
    from backend_app.core.settings import get_settings

    return float(get_settings().batch_timeout)

# ----------------------------------------------------------------------------
# GLOBAL STATE
# ----------------------------------------------------------------------------
MODEL = None
TOKENIZER = None

# Single-worker pool: GPU runs one generation at a time; event loop stays responsive.
MODEL_EXECUTOR = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="qwen-inference",
)

RESPONSE_CACHE = TTLCache(maxsize=1000, ttl=3600)

# Async job store — holds results for polling. TTL=1hr auto-cleans old jobs.
JOB_STORE = TTLCache(maxsize=500, ttl=3600)

STATS = {
    "total_requests": 0,
    "cache_hits": 0,
    "cache_misses": 0,
    "total_generation_time": 0.0,
    "requests_by_endpoint": {},
    "errors": 0,
    "batches_processed": 0,
    "total_batched_requests": 0,
    "avg_batch_size": 0.0,
    "server_start_time": None,
}

batch_queues = {
    "topics": deque(),
    "mcq": deque(),
    "subjective": deque(),
    "coding": deque(),
    "sql": deque(),
    "aiml": deque()
}

batch_locks = {endpoint: asyncio.Lock() for endpoint in batch_queues.keys()}
pending_results = {}

# Model Console: recent /api access rows (middleware)
REQUEST_LOG = deque(maxlen=2000)

# ----------------------------------------------------------------------------
# FASTAPI APP
# ----------------------------------------------------------------------------
@asynccontextmanager
async def _app_lifespan(_app: FastAPI):
    from backend_app.billing.db import ensure_indexes
    from backend_app.core.settings import get_settings

    s = get_settings()
    for p in (s.dsa_enriched_path, s.aiml_catalog_path):
        if not p.exists():
            raise RuntimeError(f"Required asset not found: {p}")
    await ensure_indexes()
    STATS["server_start_time"] = datetime.now(timezone.utc).isoformat()
    load_model()
    yield
    for q in batch_queues.values():
        q.clear()
    MODEL_EXECUTOR.shutdown(wait=False)


app = FastAPI(title="Gisul AI Platform", version="2.0.0", lifespan=_app_lifespan)

# ----------------------------------------------------------------------------
# REQUEST / RESPONSE MODELS
# ----------------------------------------------------------------------------

class TopicGenerationRequest(BaseModel):
    assessment_title: str
    job_designation: str
    skills: List[str]
    experience_min: int
    experience_max: int
    experience_mode: str = "corporate"
    num_topics: int = 10
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None

class TopicGenerationResponse(BaseModel):
    topics: List[Dict[str, Any]]
    generation_time_seconds: float
    model: str = "Qwen2.5-7B-Instruct"
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class TopicBatchResponse(BaseModel):
    topics: List[Dict[str, Any]]
    generation_time_seconds: float
    model: str = "Qwen2.5-7B-Instruct"
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

class MCQGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    target_audience: str
    num_questions: int = 1
    request_id: Optional[str] = None
    use_cache: bool = True
    org_id: Optional[str] = None

class MCQGenerationResponse(BaseModel):
    question: str
    options: List[Dict[str, Any]]
    explanation: str
    difficulty: str
    bloomLevel: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class MCQBatchResponse(BaseModel):
    questions: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

class SubjectiveGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    target_audience: str
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None

class SubjectiveGenerationResponse(BaseModel):
    question: str
    expectedAnswer: str
    gradingCriteria: List[str]
    difficulty: str
    bloomLevel: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class SubjectiveBatchResponse(BaseModel):
    questions: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

class CodingGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    language: str = "Python"
    job_role: str = "Software Engineer"
    experience_years: str = "3-5"
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None

class CodingGenerationResponse(BaseModel):
    problemStatement: str
    inputFormat: str
    outputFormat: str
    constraints: List[str]
    examples: List[Dict[str, Any]]
    testCases: List[Dict[str, Any]]
    starterCode: str
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class CodingBatchResponse(BaseModel):
    coding_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

class SQLGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    database_type: str = "PostgreSQL"
    job_role: str = "Software Engineer"
    experience_years: str = "3-5"
    num_questions: int = 1
    use_cache: bool = True
    org_id: Optional[str] = None

class SQLGenerationResponse(BaseModel):
    """``schema`` shadows BaseModel in Pydantic v2 — use ``database_schema`` in Python, JSON key ``schema``."""

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    problemStatement: str
    database_schema: Dict[str, Any] = Field(..., alias="schema")
    expectedQuery: str
    explanation: str
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class SQLBatchResponse(BaseModel):
    sql_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

class AIMLGenerationRequest(BaseModel):
    topic: str
    difficulty: str
    use_cache: bool = True
    org_id: Optional[str] = None

class AIMLGenerationResponse(BaseModel):
    problemStatement: str
    dataset: Dict[str, Any]
    expectedApproach: str
    evaluationCriteria: List[str]
    difficulty: str
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = False
    batch_size: int = 1

class AIMLBatchResponse(BaseModel):
    aiml_problems: List[Dict[str, Any]]
    generation_time_seconds: float
    cache_hit: bool = False
    batched: bool = True
    batch_size: int = 1

# ----------------------------------------------------------------------------
# MODEL LOADING
# ----------------------------------------------------------------------------

def load_model():
    global MODEL, TOKENIZER
    from backend_app.core.settings import get_settings

    s = get_settings()
    mn = s.model_name
    logger.info("Loading %s...", mn)

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )

    MODEL = AutoModelForCausalLM.from_pretrained(
        mn,
        quantization_config=bnb_config,
        device_map="auto",
        trust_remote_code=True,
    )

    TOKENIZER = AutoTokenizer.from_pretrained(
        mn,
        trust_remote_code=True,
    )

    logger.info(f"Model loaded. Memory: {torch.cuda.memory_allocated() / 1024**3:.2f} GB")


def _emit_usage_metering(
    *,
    job_id: str,
    usage_meta: dict | None,
    route: str,
    cache_hit: bool,
    latency_ms: float,
    status: str = "success",
    error_detail: str | None = None,
) -> None:
    try:
        schedule_usage_emit(
            job_id=job_id,
            usage_meta=usage_meta,
            route=route,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
            status=status,
            error_detail=error_detail,
        )
    except Exception:
        pass

# ----------------------------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------------------------

def generate_cache_key(endpoint: str, data: dict) -> str:
    payload = data.copy()
    request_id = payload.pop("request_id", None)
    payload.pop("use_cache", None)
    base = f"{endpoint}:{json.dumps(payload, sort_keys=True)}"
    if request_id:
        base += f":{request_id}"
    return hashlib.md5(base.encode()).hexdigest()

def get_from_cache(cache_key: str):
    if cache_key in RESPONSE_CACHE:
        STATS["cache_hits"] += 1
        return RESPONSE_CACHE[cache_key]
    STATS["cache_misses"] += 1
    return None

def save_to_cache(cache_key: str, response: Dict):
    RESPONSE_CACHE[cache_key] = response

def update_stats(endpoint: str):
    STATS["total_requests"] += 1
    if endpoint not in STATS["requests_by_endpoint"]:
        STATS["requests_by_endpoint"][endpoint] = 0
    STATS["requests_by_endpoint"][endpoint] += 1

def flatten_nested_fields(obj: dict) -> dict:
    flattened = {}
    for key, value in obj.items():
        if isinstance(value, dict):
            if len(value) == 1 and 'description' in value:
                flattened[key] = value['description']
            elif len(value) == 1 and 'code' in value:
                flattened[key] = value['code']
            elif len(value) == 1 and 'text' in value:
                flattened[key] = value['text']
            else:
                flattened[key] = value
        elif isinstance(value, list):
            flattened[key] = [
                item['description'] if isinstance(item, dict) and len(item) == 1 and 'description' in item
                else item['text'] if isinstance(item, dict) and len(item) == 1 and 'text' in item
                else item
                for item in value
            ]
        else:
            flattened[key] = value
    return flattened


# ============================================================================
# extract_json — string-aware brace counting, no silent corruption
# FIX 5: Only call validate_and_fix_aiml_response when "dataset" key present.
#         Previously called on every JSON including MCQ/SQL/coding responses.
# ============================================================================

def extract_json(text: str) -> dict:
    text = re.sub(r'```json\s*', '', text)
    text = re.sub(r'```\s*', '', text)
    text = text.strip()
    # Remove control characters that break JSON parsing
    text = re.sub(r'(?<!\\)[\x00-\x08\x0b\x0c\x0e-\x1f]', ' ', text)
    # Normalize raw newlines inside JSON string values to a space
    # This fixes SQL queries that span multiple lines inside "expectedQuery"
    text = re.sub(r'(?<!\\)\n', ' ', text)

    start = text.find('{')
    if start == -1:
        raise ValueError("No JSON object found in response")

    depth = 0
    end = -1
    in_string = False
    i = start

    while i < len(text):
        ch = text[i]
        if in_string:
            if ch == '\\':
                i += 2
                continue
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch == '{':
                depth += 1
            elif ch == '}':
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
        cleaned = re.sub(r',\s*([}\]])', r'\1', json_str)
        try:
            obj = json.loads(cleaned)
        except json.JSONDecodeError as e2:
            raise ValueError(f"JSON parse failed after cleanup: {str(e2)[:300]}")

    obj = flatten_nested_fields(obj)

    # FIX 5: Only run AIML validation when the response actually has a dataset key.
    # Previously this ran on every MCQ/subjective/SQL response unnecessarily.
    if "dataset" in obj:
        obj = validate_and_fix_aiml_response(obj)

    return obj


# ============================================================================
# MCQ PROMPT BUILDERS
# FIX 6: Comprehensive domain-aware generation prompt with correct rules for
#         Python, JS/Node, React, Next.js, SQL, TypeScript, Java, System Design,
#         OOP, Git, Docker, REST, Algorithms, Data Structures, Cloud/AWS, CS.
#
# ROUTING FIX (v7.1):
#   _CODE_TOPIC_KEYWORDS now contains ONLY execution-specific signals.
#   Broad language names ('python') and concept topics ('decorator', 'closure',
#   'recursion', 'scope', 'lambda', 'asyncio', 'generator', 'dictionary',
#   'mutable default', bare 'list comprehension') have been REMOVED.
#   Those topics must go to the conceptual pipeline where the LLM generates a
#   full theory/framework question — NOT an output-prediction execution question.
#
#   Deterministic pipeline triggers ONLY when the topic is unambiguously about
#   executing or predicting the output of a Python expression:
#     • slicing / slice / list slicing / string slicing
#     • list indexing / string indexing / index notation / negative indexing
#     • output prediction / what is the output / predict the output
#     • code output / python output / print result / print output
#     • list comprehension OUTPUT (with the word "output" present)
#     • generator expression output / lambda output / async output
#     • code execution / expression evaluation
# ============================================================================

# ---------------------------------------------------------------------------
# _CODE_TOPIC_KEYWORDS — execution-signal keywords only.
#
# RULE: A keyword belongs here if and only if the topic is SPECIFICALLY asking
#       about running / evaluating / predicting the result of Python code.
#
# NOT included (these are concept topics → conceptual pipeline):
#   'python'           — matches "Python decorators", "Python OOP", etc.
#   'decorator'        — concept topic
#   'closure'          — concept topic
#   'recursion'        — concept topic
#   'scope'            — concept topic
#   'lambda'           — concept topic (bare); only 'lambda output' is execution
#   'asyncio'          — concept topic
#   'generator'        — concept topic (bare); only 'generator expression output' is execution
#   'dictionary'       — concept topic
#   'mutable default'  — concept/gotcha topic, not pure execution
#   'list comprehension' (bare) — concept topic; only 'list comprehension output' is execution
# ---------------------------------------------------------------------------
_CODE_TOPIC_KEYWORDS = [
    # ── Slicing / indexing ────────────────────────────────────────────────
    # These unambiguously describe expression-output questions.
    'slicing',
    'slice',
    'list slicing',
    'string slicing',
    'list indexing',
    'string indexing',
    'index notation',
    'negative indexing',

    # ── Explicit output-prediction framing ───────────────────────────────
    # Any topic phrased this way is asking the student to evaluate an expression.
    'output prediction',
    'what is the output',
    'predict the output',
    'code output',
    'python output',
    'print result',
    'print output',

    # ── Comprehension / generator — ONLY with 'output' qualifier ─────────
    # "list comprehension" alone is a concept topic; "list comprehension output"
    # is an execution question. The qualifier ensures correct routing.
    'list comprehension output',
    'generator expression output',

    # ── Lambda / async — ONLY with 'output' qualifier ────────────────────
    'lambda output',
    'async output',

    # ── Generic code-execution phrasings ─────────────────────────────────
    'code execution',
    'expression evaluation',
]


def build_mcq_context_prompt(req: dict) -> str:
    """
    Deterministic-first prompt: LLM generates context ONLY (no correct answer).
    System executes the expression and builds the correct answer itself.
    Used for all Python output-prediction / executable MCQs.
    """
    return f"""
You are generating raw material for a Python output-prediction MCQ.
Topic: {req['topic']}
Difficulty: {req['difficulty']}
Audience: {req['target_audience']}

YOUR ONLY JOB: Generate the code scenario. Do NOT compute or include the correct answer.
The system will execute the code and determine the correct answer automatically.

STRICT RULES:
- setup_code: 1-5 lines of plain Python assignments/definitions. No imports.
  Must be self-contained and executable as-is.
- expression: ONE single Python expression that can be evaluated with eval().
  No print(). No assignment. No semicolons. Just the expression itself.
  Example: "numbers[1::2]"  or  "len(data) * 2"  or  "sorted(d.items())"
- distractors: exactly 3 WRONG answers a student commonly guesses.
  Must be plausible Python literal values — NOT the real output.
  Must differ from each other and from the real answer.
  Use common off-by-one errors, wrong step values, wrong indices.
- explanation_template: explain the concept clearly. Use the exact placeholder
  {{CORRECT_ANSWER}} where the computed result should appear.
- question: full question text including the code and the expression to evaluate.
  Format it as: "Given:\\n\\n<setup_code>\\n\\nWhat is the value of: <expression>"
- Do NOT include the correct answer anywhere in this JSON. Not in distractors,
  not in explanation_template, not in question. The system computes it.
- Return ONLY valid JSON — no markdown, no extra text.

PYTHON RULES (generate correct setup_code and expression):
- List slicing never raises IndexError — out-of-range slices return empty list.
- [::-1] reverses the entire sequence.
- dict.items(), .keys(), .values() return views in Python 3 — wrap in list() if needed.
- Mutable default arguments persist across calls.
- is vs == : is checks identity, == checks equality.
- range() is lazy; list(range(n)) gives a list.

JSON FORMAT (return exactly this structure):
{{
  "question": "Given:\\n\\nnumbers = [10, 20, 30, 40, 50]\\n\\nWhat is the value of: numbers[1::2]",
  "setup_code": "numbers = [10, 20, 30, 40, 50]",
  "expression": "numbers[1::2]",
  "distractors": ["[10, 30, 50]", "[20, 40]", "[10, 20, 30]"],
  "explanation_template": "The slice [1::2] starts at index 1 and steps by 2, picking every second element from index 1 onward. The result is {{CORRECT_ANSWER}}.",
  "difficulty": "{req['difficulty']}",
  "bloomLevel": "Apply"
}}
"""


def build_mcq_prompt(req: dict) -> str:
    topic_lower = req['topic'].lower()

    # -------------------------------------------------------------------------
    # ROUTING: deterministic pipeline vs conceptual pipeline
    #
    # Check whether any execution-specific keyword is present in the topic.
    # _CODE_TOPIC_KEYWORDS contains ONLY slicing/indexing/output-prediction
    # signals — NOT broad language names or concept-level topics.
    #
    # Examples that DO route here (deterministic):
    #   "Python list slicing"             → 'list slicing' matches
    #   "String slicing with step"        → 'slicing' matches
    #   "Output prediction: list indexing"→ 'output prediction' matches
    #   "What is the output of slicing"   → 'what is the output' matches
    #
    # Examples that do NOT route here (conceptual):
    #   "Python decorators"               → no execution keyword present
    #   "Python closures"                 → no execution keyword present
    #   "Python OOP"                      → no execution keyword present
    #   "Asyncio fundamentals"            → no execution keyword present
    #   "List comprehension basics"       → bare 'list comprehension' not in list
    #   "Lambda functions"                → bare 'lambda' not in list
    # -------------------------------------------------------------------------
    if any(k in topic_lower for k in _CODE_TOPIC_KEYWORDS):
        return build_mcq_context_prompt(req)

    # Detect domain for domain-specific guidance injection
    domain_hint = ""

    if any(k in topic_lower for k in ['python', 'slicing', 'list comprehension', 'generator', 'decorator', 'gil', 'asyncio']):
        domain_hint = """
PYTHON-SPECIFIC RULES:
- List slicing never raises IndexError — out-of-range slices return empty list.
- [::-1] reverses the entire sequence.
- range() is lazy; list(range()) is a list.
- dict.items(), .keys(), .values() return views, not lists, in Python 3.
- Mutable default arguments (e.g. def f(x=[])) persist across calls — classic bug.
- Global variables require the `global` keyword to be reassigned inside functions.
- is vs == : 'is' checks identity, '==' checks equality.
- For output prediction questions: include FULL executable code inline (no fences).
- Options MUST be pure Python literal values (e.g. [1,2,3], True, 'hello').
"""
    elif any(k in topic_lower for k in ['javascript', 'node', 'nodejs', 'es6', 'promise', 'async/await', 'closure', 'hoisting', 'event loop']):
        domain_hint = """
JAVASCRIPT/NODE-SPECIFIC RULES:
- var is function-scoped and hoisted; let/const are block-scoped.
- typeof null === 'object' is a known quirk.
- == does type coercion; === does strict comparison.
- Promises: .then() runs asynchronously even when already resolved.
- async functions always return a Promise.
- Arrow functions do NOT have their own `this`.
- NaN !== NaN; use Number.isNaN() to check.
- Node.js require() is synchronous; import is static and hoisted.
- Event loop: microtasks (Promise callbacks) run before macrotasks (setTimeout).
"""
    elif any(k in topic_lower for k in ['react', 'hooks', 'usestate', 'useeffect', 'jsx', 'component', 'props', 'virtual dom']):
        domain_hint = """
REACT-SPECIFIC RULES:
- useState setter is asynchronous — state does NOT update in the same render cycle.
- useEffect with [] runs only on mount, NOT on every render.
- useEffect with no dependency array runs after EVERY render.
- Keys in lists must be unique and stable — never use array index as key when items can reorder.
- props are READ-ONLY — components must not mutate their props.
- Conditional rendering with && short-circuit: {0 && <Comp/>} renders 0, not nothing.
- React batches state updates in event handlers (React 18+).
- useRef does not trigger re-renders when ref.current changes.
"""
    elif any(k in topic_lower for k in ['next.js', 'nextjs', 'next js', 'app router', 'pages router', 'getserversideprops', 'getstaticprops', 'ssr', 'ssg', 'isr']):
        domain_hint = """
NEXT.JS-SPECIFIC RULES:

ROUTER CONSISTENCY (CRITICAL - READ FIRST):
- Next.js has TWO routers: Pages Router (pages/ dir) and App Router (app/ dir).
- You MUST pick exactly ONE router for the entire question. NEVER mix them.
- If your question shows an app/ directory structure: ALL options MUST use App Router patterns only.
- If your question shows a pages/ directory structure: ALL options MUST use Pages Router patterns only.
- FORBIDDEN: Showing app/blog/[id]/page.tsx in question but using getServerSideProps in options.
- FORBIDDEN: Showing pages/blog/[id].js in question but using useParams() from next/navigation.
- If unsure which router to use: default to Pages Router for getServerSideProps/getStaticProps questions,
  and App Router for useParams/Server Component questions.

PAGES ROUTER (pages/ directory):
- pages/about.js maps to route /about (NEVER /pages/about).
- pages/api/users.js maps to /api/users (NEVER /pages/api/users).
- Dynamic: pages/blog/[id].js maps to /blog/:id. Access via useRouter().query.id or context.params.id.
- SSR (every request): export async function getServerSideProps(context)
- SSG (build time): export async function getStaticProps(context)
- Dynamic SSG also needs: export async function getStaticPaths()
- ISR: getStaticProps with return value containing revalidate: N
- Client-side fetch: useRouter() for params, then useEffect + fetch or SWR/React Query.

APP ROUTER (app/ directory - Next.js 13+):
- app/about/page.tsx maps to route /about.
- app/blog/[id]/page.tsx maps to route /blog/:id.
- Server Components (default): async component, fetch data directly with await fetch(). NO getServerSideProps.
- Client Components: add 'use client' directive at top of file.
- Get dynamic params in Client Component: useParams() from 'next/navigation'.
- Get dynamic params in Server Component: props.params.id directly.
- Client-side fetch: 'use client' + useParams() + useEffect + fetch, or SWR/React Query.
- getServerSideProps, getStaticProps, getStaticPaths do NOT exist in App Router.

DATA FETCHING (which function goes where):
- SSR every-request (Pages Router only) = getServerSideProps
- SSG at build time (Pages Router only) = getStaticProps
- Server Component data (App Router only) = async component + fetch() with cache settings
- Client-side fetch (both routers) = useEffect + fetch, SWR, or React Query
- getServerSideProps and getStaticProps are NEVER used in App Router. NEVER.
"""
    elif any(k in topic_lower for k in ['sql', 'database', 'query', 'join', 'group by', 'having', 'index', 'normalization', 'transaction']):
        domain_hint = """
SQL-SPECIFIC RULES:
- JOIN without ON is a CROSS JOIN (cartesian product), NOT an INNER JOIN.
- WHERE filters rows BEFORE grouping; HAVING filters AFTER grouping.
- GROUP BY must include all non-aggregated SELECT columns.
- NULL comparisons MUST use IS NULL / IS NOT NULL, never = NULL.
- COUNT(*) counts all rows; COUNT(col) skips NULLs.
- DISTINCT removes duplicate rows; UNIQUE is a constraint.
- Subquery in WHERE with IN: NULLs in the subquery result cause unexpected no-matches.
- PRIMARY KEY implies UNIQUE + NOT NULL.
- TRUNCATE vs DELETE: TRUNCATE is DDL and cannot be rolled back in most RDBMS.
- CHAR is fixed-length; VARCHAR is variable-length.
"""
    elif any(k in topic_lower for k in ['typescript', 'ts', 'interface', 'type alias', 'generic', 'enum', 'union', 'intersection']):
        domain_hint = """
TYPESCRIPT-SPECIFIC RULES:
- interface and type alias are mostly interchangeable but interface supports declaration merging.
- any disables type checking; unknown forces type checking before use — prefer unknown.
- Type assertions (as) do not perform runtime checks.
- Enums compile to objects at runtime; const enum inlines values and produces no runtime object.
- Optional chaining (?.) returns undefined, not null, if the chain is broken.
- Nullish coalescing (??) triggers only on null/undefined, not on 0 or ''.
- Generics are erased at runtime — no runtime type information from generics.
- never is the return type of functions that never return (throw or infinite loop).
"""
    elif any(k in topic_lower for k in ['java', 'jvm', 'spring', 'oop', 'inheritance', 'polymorphism', 'interface', 'abstract', 'garbage collection']):
        domain_hint = """
JAVA/OOP-SPECIFIC RULES:
- Java passes object references by value — the reference is copied, not the object.
- == compares references for objects; .equals() compares content.
- String pool: string literals are interned; new String("x") creates a new object.
- abstract class can have implementation; interface (pre-Java 8) cannot.
- Java 8+: interfaces can have default and static methods.
- final class cannot be extended; final method cannot be overridden; final variable cannot be reassigned.
- Autoboxing: int ↔ Integer. Integer cache applies only for values -128 to 127.
- Checked exceptions must be declared or caught; unchecked (RuntimeException) need not be.
- super() must be the FIRST statement in a constructor if used.
- Garbage collection: objects are eligible when no live references remain.
"""
    elif any(k in topic_lower for k in ['git', 'version control', 'merge', 'rebase', 'branch', 'commit', 'cherry-pick', 'stash']):
        domain_hint = """
GIT-SPECIFIC RULES:
- git merge creates a merge commit preserving full history.
- git rebase rewrites commit history — do NOT rebase shared/public branches.
- git reset --hard destroys uncommitted changes permanently.
- git revert creates a NEW commit that undoes a previous commit (safe for shared branches).
- git stash saves dirty working directory temporarily; git stash pop restores it.
- git cherry-pick applies a specific commit from another branch.
- Detached HEAD: HEAD points to a commit, not a branch — commits can be lost.
- git pull = git fetch + git merge (or rebase with --rebase flag).
- origin/main is a remote-tracking branch, not the remote itself.
"""
    elif any(k in topic_lower for k in ['docker', 'container', 'kubernetes', 'k8s', 'image', 'dockerfile', 'volume', 'network', 'pod']):
        domain_hint = """
DOCKER/KUBERNETES-SPECIFIC RULES:
- Docker images are immutable layers; containers are running instances of images.
- COPY vs ADD: COPY is preferred; ADD can auto-extract tarballs (use only when needed).
- CMD sets default command; ENTRYPOINT sets fixed command. CMD args override; ENTRYPOINT args append.
- ENV sets environment variables at build AND runtime; ARG only at build time.
- Volumes persist data beyond container lifecycle; bind mounts link to host filesystem.
- Docker networking: bridge (default), host (no isolation), none.
- Kubernetes Pod = smallest deployable unit; can contain multiple containers.
- kubectl apply is declarative; kubectl create is imperative.
- ConfigMap stores non-sensitive config; Secret stores sensitive config (base64 encoded, NOT encrypted by default).
- Liveness probe: restarts container if it fails; Readiness probe: removes from service if it fails.
"""
    elif any(k in topic_lower for k in ['rest', 'api', 'http', 'status code', 'authentication', 'jwt', 'oauth', 'graphql', 'websocket']):
        domain_hint = """
REST/API-SPECIFIC RULES:
- GET is idempotent and safe (no side effects); POST is neither.
- PUT replaces the entire resource; PATCH applies partial updates.
- DELETE is idempotent (deleting already-deleted resource returns 404 or 204, same result).
- 200 OK, 201 Created, 204 No Content, 400 Bad Request, 401 Unauthorized, 403 Forbidden,
  404 Not Found, 409 Conflict, 422 Unprocessable Entity, 500 Internal Server Error.
- JWT: header.payload.signature — payload is base64 encoded, NOT encrypted.
- OAuth2: Authorization Code flow for web apps; Client Credentials for machine-to-machine.
- CORS: preflight OPTIONS request is sent before cross-origin requests with custom headers.
- REST is stateless — server stores no session state between requests.
- GraphQL: single endpoint, client specifies exact fields needed (no over/under-fetching).
"""
    elif any(k in topic_lower for k in ['algorithm', 'data structure', 'big o', 'complexity', 'sorting', 'graph', 'tree', 'binary search', 'hash', 'linked list', 'stack', 'queue', 'heap', 'dp', 'dynamic programming']):
        domain_hint = """
ALGORITHMS/DATA STRUCTURES-SPECIFIC RULES:
- Big O measures asymptotic worst-case growth, not exact runtime.
- O(1) < O(log n) < O(n) < O(n log n) < O(n²) < O(2^n) < O(n!)
- Binary search requires a SORTED array; O(log n).
- Hash table average O(1) lookup; worst case O(n) due to collisions.
- BFS uses a queue; DFS uses a stack (or recursion).
- BFS finds shortest path in unweighted graphs; Dijkstra for weighted graphs.
- In-order traversal of BST gives sorted output.
- Heap: parent is always larger (max-heap) or smaller (min-heap) than children.
- Dynamic programming requires overlapping subproblems and optimal substructure.
- Quicksort average O(n log n), worst O(n²); Mergesort always O(n log n) but needs O(n) space.
- Linked list: O(n) access, O(1) insert/delete at head.
"""
    elif any(k in topic_lower for k in ['aws', 'cloud', 'azure', 's3', 'ec2', 'lambda', 'gcp', 'serverless', 'vpc', 'iam']):
        domain_hint = """
CLOUD/AWS-SPECIFIC RULES:
- S3 is object storage (not a file system); keys are flat, folders are prefixes.
- EC2 is IaaS; Lambda is FaaS (serverless, stateless, ephemeral).
- IAM: Users have credentials; Roles are assumed by services/instances.
- IAM policies: explicit Deny overrides any Allow.
- VPC: private network inside AWS; subnets can be public (internet gateway) or private.
- Security Groups are stateful (return traffic auto-allowed); NACLs are stateless.
- RDS: managed relational DB; DynamoDB: managed NoSQL key-value/document store.
- CloudFront: CDN (edge caching); Route 53: DNS service.
- Lambda cold start: first invocation has latency; provisioned concurrency eliminates it.
- SQS: message queue (pull); SNS: pub/sub notifications (push).
"""
    elif any(k in topic_lower for k in ['system design', 'scalability', 'load balancer', 'caching', 'microservices', 'message queue', 'cdn', 'sharding', 'cap theorem', 'consistency']):
        domain_hint = """
SYSTEM DESIGN-SPECIFIC RULES:
- CAP theorem: Consistency, Availability, Partition Tolerance — can only guarantee 2 of 3.
- CP systems (Zookeeper, HBase): consistent but may be unavailable during partition.
- AP systems (Cassandra, DynamoDB): available but may return stale data during partition.
- Horizontal scaling: add more machines. Vertical scaling: add more resources to one machine.
- Load balancer distributes traffic; does NOT cache responses (that's a CDN/reverse proxy).
- Write-through cache: write to cache AND DB simultaneously.
- Write-back cache: write to cache first, DB later (faster but risk of data loss).
- Read-through cache: application reads from cache; cache fetches from DB on miss.
- Message queues decouple producers and consumers; enable async processing.
- Sharding (horizontal partitioning) splits data across multiple DB instances.
- Consistent hashing minimizes reshuffling when nodes are added/removed.
"""
    else:
        domain_hint = """
GENERAL TECHNICAL RULES:
- Answer must be unambiguous — only ONE option is defensibly correct.
- Avoid trick questions based on obscure edge cases.
- Prefer standard, widely-accepted behavior over implementation-specific quirks.
- Do not mix concepts from different language versions unless explicitly stated.
"""

    return f"""
You are a senior technical examiner creating professional assessment questions.

Create ONE {req['difficulty']} multiple-choice question about: {req['topic']}
Target audience: {req['target_audience']}

{domain_hint}

UNIVERSAL STRICT RULES:
- Write a COMPLETE, REAL question — NO placeholders like "...", "example", or "TBD".
- EXACTLY ONE option must be correct. All other three must be clearly incorrect.
- Explanation MUST match the correct option and explain WHY others are wrong.
- For output prediction questions: include FULL executable code inline as plain text lines.
- Do NOT use triple backticks, code fences, or language labels before code.
- Do NOT write "python" or "javascript" as a standalone word before code.
- Write code directly as plain indented lines.
- For code questions: options MUST be pure literal values (e.g. [1,2,3], True, 'hello', 42).
- Do NOT include explanation text inside options.
- Return ONLY valid JSON — no markdown, no extra text outside the JSON.

ANTI-AMBIGUITY RULES (CRITICAL):
- Do NOT use vague phrases: "best practice", "recommended approach", "modern way",
  "latest method", "preferred way", "most efficient", "correct way" — unless the question
  is locked to a specific version or documented constraint.
- If framework version matters: state it explicitly.
  GOOD: "In Next.js App Router (Next.js 13+), which hook gets dynamic route params in a Client Component?"
  BAD:  "What is the best way to get route params in Next.js?"
- Rewrite opinion-based questions as factual, constraint-based questions so only ONE answer
  is correct from official documentation.
  GOOD: "Which Next.js Pages Router function fetches data on every server request?"
  BAD:  "What is the recommended data fetching method in Next.js?"
- Never mark an officially documented API as wrong unless the question explicitly
  excludes it (e.g. "without using getServerSideProps").
- ALL code snippets inside options must be syntactically valid. An option with
  undefined variables, missing imports, or syntax errors is INVALID and must not be used.

OPTION QUALITY RULES:
- All 4 options must be plausible — avoid obviously absurd distractors.
- Distractors should represent common mistakes or misconceptions.
- Options should be similar in length and format.
- For conceptual questions: options should cover the most commonly confused alternatives.

JSON FORMAT (strict):
{{
  "question": "Complete question text with all code/context included",
  "options": [
    {{"label": "A", "text": "...", "isCorrect": false}},
    {{"label": "B", "text": "...", "isCorrect": true}},
    {{"label": "C", "text": "...", "isCorrect": false}},
    {{"label": "D", "text": "...", "isCorrect": false}}
  ],
  "explanation": "Detailed explanation of WHY option B is correct and why A, C, D are wrong.",
  "difficulty": "{req['difficulty']}",
  "bloomLevel": "Apply"
}}
"""


def build_mcq_verifier_prompt(mcq: dict) -> str:
    return f"""
You are a STRICT exam quality validator and senior multi-domain technical specialist.

GOAL:
Ensure this MCQ is technically accurate, unambiguous, and suitable for a real
professional or university technical assessment.

VALIDATION RULES (MANDATORY):
1. There MUST be EXACTLY ONE correct option.
2. If more than one option is logically correct, modify so ONLY ONE remains correct.
3. Prefer the MOST DIRECT, UNAMBIGUOUS, and STANDARD solution.
4. All other options MUST be clearly incorrect.
5. The explanation MUST justify the correct option AND briefly note why others are wrong.
6. If code is present: verify the output step-by-step. Do NOT guess.
7. Remove ambiguity, edge cases, or trick interpretations.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DOMAIN-SPECIFIC VALIDATION RULES (ALL MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

PYTHON:
- List slicing NEVER raises IndexError.
- [::-1] reverses entire sequence.
- is vs ==: is checks object identity, == checks value equality.
- Mutable default args persist across function calls.
- dict views (.items/.keys/.values) are NOT lists in Python 3.
- Chained comparisons like 1 < x < 10 are valid Python.

JAVASCRIPT / NODE.JS:
- var is function-scoped and hoisted (initialized as undefined).
- let/const are block-scoped; accessing before declaration → ReferenceError.
- typeof null === 'object' (historical quirk).
- == does type coercion; === does not.
- Arrow functions have no own `this` binding.
- Promises: microtasks run BEFORE macrotasks (setTimeout).
- async functions ALWAYS return a Promise.
- NaN !== NaN; use Number.isNaN() or Object.is(x, NaN).

REACT:
- useState setter is ASYNCHRONOUS within the same render.
- useEffect([]) fires on mount ONLY.
- useEffect() with no deps fires after EVERY render.
- Keys must be stable — avoid array index when list can reorder/delete.
- props are read-only; never mutate props directly.
- {{0 && <Comp/>}} renders 0 (falsy number), not nothing.
- useSWR/useQuery require the dynamic parameter (e.g. id) to be obtained FIRST via useRouter() or useParams() before constructing the URL. A snippet that uses id in useSWR without defining id first is BROKEN code and MUST be marked wrong.

NEXT.JS:
- /pages/ is a filesystem convention, NEVER part of a URL.
- pages/about.js → route /about (NOT /pages/about).
- pages/api/users.js → /api/users (NOT /pages/api/users).
- SSR (every request) = getServerSideProps ONLY (Pages Router only).
- SSG (build time) = getStaticProps ONLY (Pages Router only).
- ISR = getStaticProps + {{ revalidate: N }} (Pages Router only).
- getServerSideProps and getStaticProps are NEVER interchangeable.
- App Router: app/about/page.tsx → /about.
- App Router Client Component: requires 'use client' + useParams() from 'next/navigation'.
- App Router Server Component: async component, fetch directly with await, NO getServerSideProps.
- getServerSideProps / getStaticProps / getStaticPaths do NOT exist in App Router. EVER.

NEXT.JS ROUTER MIXING CHECK (MANDATORY — check BEFORE validating options):
- Read the directory structure shown in the question.
- If it shows app/ directory: ALL options must use App Router patterns only.
  - INVALID in App Router options: getServerSideProps, getStaticProps, getStaticPaths.
  - VALID in App Router options: 'use client', useParams(), async Server Component, fetch().
- If it shows pages/ directory: ALL options must use Pages Router patterns only.
  - INVALID in Pages Router options: useParams() from 'next/navigation', Server Components.
  - VALID in Pages Router options: getServerSideProps, getStaticProps, useRouter().query.
- If ANY option mixes routers (e.g. app/ structure + getServerSideProps): mark that option WRONG.
- If ALL options mix routers (no option is correct for the shown directory): return rejected JSON.
- If the question itself mixes routers (app/ structure + getServerSideProps in the question text):
  fix the question to use a consistent router before validating options.

SQL:
- JOIN without ON = CROSS JOIN (cartesian product).
- WHERE filters BEFORE GROUP BY; HAVING filters AFTER.
- GROUP BY must include all non-aggregated SELECT columns.
- NULL: use IS NULL / IS NOT NULL, never = NULL.
- COUNT(*) includes NULLs; COUNT(col) excludes NULLs.
- TRUNCATE is DDL (cannot be rolled back in most RDBMS); DELETE is DML.

TYPESCRIPT:
- any disables type checking; unknown forces checking before use.
- const enum values are inlined; regular enum creates a runtime object.
- Type assertions (as) perform NO runtime checks.
- never is return type of functions that never return.
- Nullish coalescing (??) triggers only on null/undefined, NOT on 0 or ''.

JAVA / OOP:
- Java passes object references by value.
- == compares references; .equals() compares content for objects.
- String literals are interned; new String("x") creates a new heap object.
- Integer cache only applies for values -128 to 127 (autoboxing).
- abstract class can have implementation; interface (pre-Java 8) cannot.
- super() must be FIRST statement in a constructor.

GIT:
- git rebase rewrites history; never rebase shared/public branches.
- git revert is safe for shared branches (creates new undo commit).
- git reset --hard is DESTRUCTIVE — cannot be undone for uncommitted changes.
- Detached HEAD: commits can be lost if you switch branches without saving.
- git pull = fetch + merge (or rebase with --rebase).

DOCKER / KUBERNETES:
- CMD sets default; ENTRYPOINT sets fixed executable.
- ARG is build-time only; ENV persists to runtime.
- ConfigMap = non-sensitive config; Secret = sensitive (base64, NOT encrypted).
- Liveness probe restart container; Readiness probe removes from service endpoint.
- Docker images are immutable; containers are running instances.

REST / HTTP:
- GET is idempotent and safe; POST is neither.
- PUT replaces entire resource; PATCH applies partial update.
- 401 Unauthorized = not authenticated; 403 Forbidden = authenticated but no permission.
- JWT payload is base64 encoded, NOT encrypted — do NOT store secrets in payload.
- CORS preflight OPTIONS request is sent automatically by browser.

ALGORITHMS / DATA STRUCTURES:
- Binary search requires SORTED input.
- BFS uses queue (shortest path unweighted); DFS uses stack/recursion.
- Hash table: O(1) average, O(n) worst case lookup.
- Heap property: parent > children (max-heap) or parent < children (min-heap).
- Quicksort worst case O(n²); Mergesort always O(n log n) but O(n) space.
- In-order BST traversal gives sorted output.

CLOUD / AWS:
- IAM explicit Deny ALWAYS overrides Allow.
- Security Groups are stateful; NACLs are stateless.
- Lambda is stateless and ephemeral — no persistent local storage.
- S3 is object storage (not a filesystem); no true directories.
- EC2 = IaaS; Lambda = FaaS; ECS/EKS = CaaS.

SYSTEM DESIGN:
- CAP theorem: Consistency + Availability + Partition Tolerance — pick 2.
- Write-through: write to cache AND DB simultaneously.
- Write-back: write to cache first, DB lazily (risk of data loss).
- Load balancer distributes traffic; does NOT cache (CDN caches).
- Consistent hashing minimizes reshuffling when cluster nodes change.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONCEPT COMPLETENESS CHECK (MANDATORY)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Before validating, ask: "Does any option contain the TRUE correct concept?"

- If YES → proceed with normal validation.
- If NO → do NOT attempt to fix. Return EXACTLY this JSON:
  {{
    "rejected": true,
    "rejection_reason": "missing_correct_concept",
    "question": "<original question>",
    "options": <original options>,
    "explanation": "The correct concept is absent from all options. MCQ must be regenerated.",
    "difficulty": "<original difficulty>",
    "bloomLevel": "<original bloomLevel>"
  }}

Examples requiring rejection:
- SSR question but getServerSideProps absent → reject.
- React side-effects question but useEffect absent → reject.
- SQL aggregation but GROUP BY absent → reject.
- JWT question but base64/signature absent → reject.
- Next.js routing but [param] dynamic syntax absent → reject.
- Git undo question but git revert absent → reject.
- Next.js App Router question (app/ directory shown) but ALL options use getServerSideProps/getStaticProps → reject (wrong router in all options).
- Next.js client-side fetch in App Router but no option uses useParams() + useEffect/'use client' → reject.

DO NOT try to patch an MCQ when the correct concept is entirely missing.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
IF ISSUES EXIST (correct concept IS present):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Fix the question, options, and explanation.
- Preserve difficulty level.
- Return ONLY valid JSON — no markdown, no extra text.

MCQ TO VALIDATE:
{json.dumps(mcq, indent=2)}
"""


# ============================================================================
# verify_mcq_with_llm
# FIX 1: Now checks for {"rejected": true} returned by verifier when correct
#         concept is missing. Previously this was silently ignored, causing
#         deterministic validation to receive a rejected MCQ dict without
#         ever triggering a proper retry.
# ============================================================================

def verify_mcq_with_llm(mcq: dict) -> dict:
    for attempt in range(2):
        try:
            messages = [
                {"role": "system", "content": "You are a senior assessment quality auditor."},
                {"role": "user", "content": build_mcq_verifier_prompt(mcq)}
            ]
            text = TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            inputs = TOKENIZER(text, return_tensors="pt").to(MODEL.device)
            output = MODEL.generate(
                **inputs,
                max_new_tokens=2000,
                temperature=0.2,
                do_sample=True,
                top_p=0.9,
                pad_token_id=TOKENIZER.eos_token_id
            )
            decoded = TOKENIZER.decode(output[0], skip_special_tokens=True)
            decoded = decoded.split("assistant")[-1].strip()
            verified = extract_json(decoded)

            if verified.get("rejected") is True:
                rejection_reason = verified.get("rejection_reason", "unknown")
                raise RuntimeError(
                    f"LLM verifier rejected MCQ — concept missing: {rejection_reason}"
                )

            return verified

        except RuntimeError:
            raise
        except Exception as e:
            logger.warning(f"MCQ verification attempt {attempt + 1} failed: {e}")
            if attempt == 1:
                raise RuntimeError(f"MCQ verification failed after 2 attempts: {e}") from e

    raise RuntimeError("MCQ verification failed after retries")


# ============================================================================
# detect_ambiguity — catches vague/opinion-based MCQs before they pass through
# ============================================================================

# Phrases that make a question depend on opinion rather than documented fact.
_AMBIGUOUS_PHRASES = [
    "best practice",
    "best practices",
    "recommended approach",
    "recommended way",
    "modern way",
    "latest method",
    "latest approach",
    "preferred way",
    "preferred approach",
    "most efficient way",
    "correct way to",
    "right way to",
    "should you use",
    "which is better",
]

# Explanation over-claim phrases — signals the LLM is asserting opinion as fact.
_OVERCLAIM_PHRASES = [
    "the only correct",
    "the only way",
    "always use",
    "never use",
    "is outdated",
    "is deprecated",
    "is not recommended",
    "is not the best",
]

def detect_ambiguity(mcq: dict) -> tuple:
    """
    Returns (is_ambiguous: bool, reason: str).
    Checks question text for vague opinion-based phrasing and explanation over-claims.
    """
    question = mcq.get("question", "").lower()
    explanation = mcq.get("explanation", "").lower()

    for phrase in _AMBIGUOUS_PHRASES:
        if phrase in question:
            return True, f"ambiguous_question_phrasing: '{phrase}' found in question"

    for phrase in _OVERCLAIM_PHRASES:
        if phrase in explanation:
            return True, f"explanation_overclaim: '{phrase}' found in explanation"

    return False, ""


# ============================================================================
# protect_official_api_logic — prevents valid APIs from being wrongly rejected
# Context-aware: checks router type before flagging Next.js APIs
# ============================================================================

# APIs that are officially documented and valid in specific contexts.
# If an option uses one of these and is marked wrong, we check whether
# the explanation claims it is invalid WITHOUT a proper constraint.
_PROTECTED_APIS = {
    # Next.js Pages Router — valid ONLY in pages/ directory
    "getserversideprops": "pages_router",
    "getstaticprops": "pages_router",
    "getstaticpaths": "pages_router",
    # Next.js App Router — valid ONLY in app/ directory
    "useparams": "app_router",
    # React universal
    "useswr": "universal",
    "useeffect": "universal",
    "usestate": "universal",
    "usequery": "universal",
    "userouter": "universal",
}

# Phrases in the explanation that claim an API is wrong without a constraint.
_INVALID_CLAIM_PHRASES = [
    "not recommended",
    "not the best",
    "not suitable",
    "not appropriate",
    "outdated",
    "deprecated",
    "incorrect approach",
    "wrong approach",
    "should not be used",
    "cannot be used",
]

def protect_official_api_logic(mcq: dict) -> tuple:
    """
    Returns (has_violation: bool, reason: str).
    Detects when a valid official API is marked wrong AND the explanation
    claims it is generically invalid — without a specific documented constraint.

    Context-aware for Next.js: if the question shows app/ directory, then
    getServerSideProps being marked wrong is CORRECT behavior (not a false positive).
    Similarly if question shows pages/ directory, useParams being wrong is correct.
    """
    question_lower = mcq.get("question", "").lower()
    explanation_lower = mcq.get("explanation", "").lower()

    # Detect which router context the question is using
    uses_app_router = "app/" in question_lower or "use client" in question_lower
    uses_pages_router = "pages/" in question_lower and "app/" not in question_lower

    # Check if explanation contains an invalid claim phrase
    explanation_has_invalid_claim = any(
        phrase in explanation_lower for phrase in _INVALID_CLAIM_PHRASES
    )

    if not explanation_has_invalid_claim:
        return False, ""  # Explanation doesn't claim anything is invalid — no issue

    for option in mcq.get("options", []):
        if option.get("isCorrect") is True:
            continue  # Only check options marked as WRONG

        option_text_lower = option.get("text", "").lower()

        for api, context in _PROTECTED_APIS.items():
            if api not in option_text_lower:
                continue

            # Context-aware check: skip if the wrong-marking is intentional
            if context == "pages_router" and uses_app_router:
                # getServerSideProps marked wrong in App Router question = correct behavior
                continue
            if context == "app_router" and uses_pages_router:
                # useParams marked wrong in Pages Router question = correct behavior
                continue

            # API is valid in this context but explanation claims it's invalid
            return (
                True,
                f"official_api_wrongly_rejected: '{api}' marked wrong but "
                f"explanation claims it's invalid without documented constraint"
            )

    return False, ""


# ============================================================================
# is_code_mcq — confidence-based, returns (bool, "high"|"low"|"none")
# ============================================================================

def is_code_mcq(question: str) -> Tuple[bool, str]:
    HIGH_CONFIDENCE_PATTERNS = [
        r'```python',
        r'output of\s*[:\-]',
        r'what\s+is\s+the\s+output',
        r'what\s+does\s+the\s+following\s+(code|program)',
        r'what\s+will\s+.{0,30}print',
        r'print\s*\([^)]{3,}\)',
    ]
    LOW_CONFIDENCE_PATTERNS = [
        r'\[[\d\s]*:[\d\s]*\]',
        r'\[::\s*-?\d*\]',
        r'for\s+\w+\s+in\s+',
        r'def\s+\w+\s*\(',
        r'lambda\s+',
        r'\w+\s*=\s*\[',
        r'\w+\s*=\s*\(',
    ]

    for pattern in HIGH_CONFIDENCE_PATTERNS:
        if re.search(pattern, question, re.IGNORECASE | re.DOTALL):
            logger.info("Code MCQ: HIGH confidence")
            return True, "high"

    low_hits = sum(1 for p in LOW_CONFIDENCE_PATTERNS if re.search(p, question, re.IGNORECASE))
    if low_hits >= 2:
        logger.info(f"Code MCQ: LOW confidence ({low_hits} signals) — skipping execution")
        return True, "low"

    return False, "none"


# ============================================================================
# extract_setup_code — fenced-block aware
# ============================================================================

def extract_setup_code(question: str) -> str:
    fenced_match = re.search(r'```python\s*\n(.*?)```', question, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        block = fenced_match.group(1)
        setup_lines = []
        for line in block.split('\n'):
            clean = line.strip()
            if not clean:
                continue
            if re.match(r'^[a-zA-Z_]\w*\s*=(?!=)', clean):
                setup_lines.append(clean)
        if setup_lines:
            return '\n'.join(setup_lines)

    skip_markers = {'python', '```', '```python', '```python3'}
    setup_lines = []
    for line in question.split('\n'):
        clean = line.strip()
        if not clean or clean.lower() in skip_markers:
            continue
        if re.match(r'^[a-zA-Z_]\w*\s*=(?!=)', clean):
            if not re.match(r'^print\s*\(', clean):
                setup_lines.append(clean)

    return '\n'.join(setup_lines)


# ============================================================================
# extract_expression — bracket counting, fenced-block aware
# ============================================================================

def extract_expression(question: str) -> Optional[str]:
    # Strategy 1: fenced python block — use last non-assignment line
    fenced_match = re.search(r'```python\s*\n(.*?)```', question, re.DOTALL | re.IGNORECASE)
    if fenced_match:
        block_lines = [
            ln.strip() for ln in fenced_match.group(1).strip().split('\n') if ln.strip()
        ]
        if block_lines:
            last_line = block_lines[-1]
            if re.match(r'^print\s*\(', last_line):
                inner = _extract_print_inner(last_line)
                if inner:
                    return inner
            if not re.match(r'^[a-zA-Z_]\w*\s*=(?!=)', last_line):
                return last_line

    # Strategy 2: "output of: expr?" pattern
    output_of_match = re.search(
        r'output\s+of\s*[:\-]?\s*`?([^`\n?]{3,150}?)`?\s*\?',
        question,
        re.IGNORECASE
    )
    if output_of_match:
        candidate = output_of_match.group(1).strip().strip('`').strip()
        if candidate and not re.search(r'\b(the|is|are|was|were)\b', candidate, re.IGNORECASE):
            return candidate

    # Strategy 3: print() with bracket counting
    print_idx = question.find('print(')
    if print_idx != -1:
        inner = _extract_print_inner(question[print_idx:])
        if inner:
            return inner

    return None


def _extract_print_inner(text: str) -> Optional[str]:
    """Extract content inside print() using bracket counting — handles nesting."""
    start_idx = text.find('print(')
    if start_idx == -1:
        return None

    pos = start_idx + len('print(')
    depth = 1
    in_string = False
    string_char = None

    while pos < len(text) and depth > 0:
        ch = text[pos]
        if in_string:
            if ch == '\\':
                pos += 2
                continue
            if ch == string_char:
                in_string = False
        else:
            if ch in ('"', "'"):
                in_string = True
                string_char = ch
            elif ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
                if depth == 0:
                    inner = text[start_idx + len('print('):pos].strip()
                    return inner if inner else None
        pos += 1

    return None


# ============================================================================
# safe_execute — hardened subprocess sandbox
# FIX 2: env={} can fail on Linux systems that need PATH/HOME/LANG.
#         Changed to minimal safe env with only PATH set.
# FIX 3: Added r'\bfrom\s+\w+\s+import\b' to block "from os import path" etc.
#         Previously only r'\bimport\s+\w' was present, missing from-imports.
# ============================================================================

_BLOCKED_CODE_PATTERNS = [
    r'\b__import__\s*\(',
    r'\bimport\s+\w',                   # import os, import sys, etc.
    r'\bfrom\s+\w+\s+import\b',         # FIX 3: from os import path, from subprocess import run
    r'\bopen\s*\(',
    r'\beval\s*\(',
    r'\bexec\s*\(',
    r'\bcompile\s*\(',
    r'\bos\.\w',
    r'\bsys\.\w',
    r'\bsubprocess\b',
    r'__[a-zA-Z]+__\s*\(',
    r'\bgetattr\s*\(',
    r'\bsetattr\s*\(',
]

# FIX 2: Minimal safe env — empty env{} breaks python3 on some Linux systems.
# Only PATH is needed to locate python3 builtins and stdlib.
_SANDBOX_ENV = {"PATH": "/usr/bin:/usr/local/bin"}

def safe_execute(setup_code: str, expression: str) -> str:
    combined_code = (setup_code or '') + '\n' + (expression or '')

    # Strip string literals before scanning to avoid false positives on
    # questions like: x = "you cannot import this"
    code_to_scan = re.sub(r'(\'[^\']*\'|"[^"]*")', '""', combined_code)
    for pattern in _BLOCKED_CODE_PATTERNS:
        if re.search(pattern, code_to_scan):
            raise ValueError(f"Blocked pattern detected: '{pattern}'")

    clean_expression = expression.strip()
    print_inner = _extract_print_inner(clean_expression) if clean_expression.startswith('print(') else None
    if print_inner is not None:
        clean_expression = print_inner

    full_code = ""
    if setup_code and setup_code.strip():
        full_code += setup_code.strip() + "\n"
    full_code += f"_mcq_result_ = {clean_expression}\nprint(repr(_mcq_result_))"

    try:
        result = subprocess.run(
            ["python3", "-c", full_code],
            capture_output=True,
            text=True,
            timeout=5,
            env=_SANDBOX_ENV,   # FIX 2: minimal safe env instead of env={}
            cwd="/tmp"
        )
    except subprocess.TimeoutExpired:
        raise

    if result.returncode != 0:
        raise ValueError(f"Execution error: {result.stderr.strip()[:300]}")

    output = result.stdout.strip()
    if not output:
        raise ValueError("Execution produced no output")

    return output


# ============================================================================
# deterministic_validate_mcq — structured result, never silently mutates
# FIX 4: explanation_mismatch changed from "rejected" to "skipped".
#         Hard-rejecting on explanation mismatch was too aggressive — the LLM
#         often correctly paraphrases the answer without quoting the literal
#         value. "skipped" lets the LLM-verified MCQ pass through instead of
#         forcing a wasteful retry cycle.
# ============================================================================

def deterministic_validate_mcq(mcq: dict) -> dict:
    """
    Returns:
        {"status": "validated"|"skipped"|"rejected", "reason": str, "mcq": dict}
    """
    question = mcq.get("question", "")

    is_code, confidence = is_code_mcq(question)

    if not is_code:
        return {"status": "skipped", "reason": "not_a_code_mcq", "mcq": mcq}
    if confidence == "low":
        return {"status": "skipped", "reason": "low_confidence_code_detection", "mcq": mcq}

    setup_code = extract_setup_code(question)
    expression = extract_expression(question)

    if not expression:
        return {"status": "skipped", "reason": "expression_not_extractable", "mcq": mcq}

    try:
        actual_output = safe_execute(setup_code, expression)
    except subprocess.TimeoutExpired:
        logger.warning("Execution timed out — skipping")
        return {"status": "skipped", "reason": "execution_timeout", "mcq": mcq}
    except ValueError as e:
        err_str = str(e).lower()
        if any(k in err_str for k in ["nameerror", "syntaxerror", "typeerror", "indexerror", "valueerror"]):
            return {"status": "rejected", "reason": f"execution_error: {str(e)[:200]}", "mcq": mcq}
        logger.warning(f"Sandbox error (skip): {e}")
        return {"status": "skipped", "reason": f"sandbox_error: {str(e)[:100]}", "mcq": mcq}
    except Exception as e:
        logger.warning(f"Unexpected execution error (skip): {e}")
        return {"status": "skipped", "reason": f"unexpected_error: {str(e)[:100]}", "mcq": mcq}

    # Compare actual output against each option
    matched_options = []
    for option in mcq.get("options", []):
        option_text = option.get("text", "").strip()
        if not option_text:
            continue
        matched = False
        try:
            if ast.literal_eval(option_text) == ast.literal_eval(actual_output):
                matched = True
        except (ValueError, SyntaxError):
            pass
        if not matched and _normalize_str(option_text) == _normalize_str(actual_output):
            matched = True
        if matched:
            matched_options.append(option)

    if len(matched_options) == 0:
        # Check if all options are prose — if so, skip instead of reject
        parseable = sum(1 for o in mcq.get("options", []) if _safe_literal_eval(o.get("text", "")))
        if parseable == 0:
            return {"status": "skipped", "reason": "options_are_prose_not_literals", "mcq": mcq}
        logger.warning(f"No option matches actual output '{actual_output}'")
        return {"status": "rejected", "reason": f"no_option_matches_actual_output:{actual_output}", "mcq": mcq}

    if len(matched_options) > 1:
        return {"status": "skipped", "reason": f"multiple_options_match_output:{actual_output}", "mcq": mcq}

    # Exactly 1 match — auto-correct isCorrect flags
    corrected_mcq = mcq.copy()
    corrected_mcq["options"] = [dict(o) for o in mcq["options"]]
    for option in corrected_mcq["options"]:
        option["isCorrect"] = (
            option.get("text", "").strip() == matched_options[0].get("text", "").strip()
        )

    # ── Explanation consistency check ─────────────────────────────────────────
    # We verify the explanation references the actual output.
    # FIX 4: Changed from hard "rejected" to "skipped" on mismatch.
    #         LLMs legitimately paraphrase answers (e.g. "every alternate element
    #         starting from index 1" instead of literally "[7, 11]"). Hard-rejecting
    #         this caused unnecessary retries for perfectly valid explanations.
    #         Now we log a warning and skip, trusting the LLM-verified version.
    explanation_raw    = corrected_mcq.get("explanation", "")
    explanation_norm   = _normalize_str(explanation_raw)
    actual_output_norm = _normalize_str(actual_output)

    if actual_output_norm not in explanation_norm:
        logger.warning(
            f"Explanation may not reference actual output '{actual_output}' — "
            f"allowing through (explanation: '{explanation_raw[:80]}')"
        )
        # FIX 4: skipped (not rejected) — explanation paraphrase is acceptable.
        # The isCorrect flags are already corrected above, so we return the
        # corrected MCQ as validated rather than discarding good work.

    corrected_mcq["validation_status"] = "validated_deterministically"
    logger.info(f"Auto-corrected to option '{matched_options[0].get('label', '?')}'")
    return {"status": "validated", "reason": "exact_match", "mcq": corrected_mcq}


def _normalize_str(s: str) -> str:
    return re.sub(r'\s+', ' ', s.strip().lower())

def _safe_literal_eval(s: str) -> bool:
    try:
        ast.literal_eval(s)
        return True
    except Exception:
        return False


# ============================================================================
# BATCH GENERATION
# ============================================================================

def generate_batch(prompts: List[str]):
    messages = []
    for p in prompts:
        messages.append([
            {
                "role": "system",
                "content": (
                    "You are an expert assessment content generator. "
                    "Always generate complete, meaningful questions and answers. "
                    "Never use placeholders like '...' or 'TBD'."
                )
            },
            {"role": "user", "content": p}
        ])

    texts = [
        TOKENIZER.apply_chat_template(m, tokenize=False, add_generation_prompt=True)
        for m in messages
    ]

    inputs = TOKENIZER(texts, return_tensors="pt", padding=True, truncation=True).to(MODEL.device)

    start = time.time()
    outputs = MODEL.generate(
        **inputs,
        max_new_tokens=2000,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        do_sample=True,
        pad_token_id=TOKENIZER.eos_token_id
    )
    duration = time.time() - start

    responses = [
        TOKENIZER.decode(o, skip_special_tokens=True).split("assistant")[-1].strip()
        for o in outputs
    ]
    return responses, duration / len(prompts)


# ============================================================================
# build_deterministic_mcq — system builds final MCQ from executed output
# ============================================================================

def _generate_fallback_distractors(actual_output: str, existing: list) -> list:
    """
    Generate type-aware, realistic fallback distractors for Python output-prediction
    MCQs when the LLM has leaked the correct answer into its own distractor list.

    Design principles:
      - Mutations are ordered from MOST realistic (common student mistake) to LEAST.
      - Every mutation stays type-consistent with actual_output where possible.
      - Nothing collides with actual_output or with any existing accepted distractor.
      - The final safety net guarantees we always reach N=3 regardless of value type.

    Returns a list of repr()-compatible strings in the same format as safe_execute().
    """
    used = set()
    used.add(_normalize_str(actual_output))
    for d in existing:
        used.add(_normalize_str(str(d)))

    def _is_fresh(c: str) -> bool:
        return _normalize_str(c) not in used

    def _try(c: str, out: list) -> None:
        """Accept c into out if fresh; always marks used so we never retry it."""
        norm = _normalize_str(c)
        if norm not in used:
            used.add(norm)
            out.append(c)
        else:
            used.add(norm)   # still mark so duplicate attempts are silently skipped

    candidates: list = []

    try:
        value = ast.literal_eval(actual_output)
    except Exception:
        value = actual_output   # treat as opaque str; handled in str branch below

    vtype = type(value)

    # ── LIST ──────────────────────────────────────────────────────────────────
    if vtype is list:
        lst = list(value)          # working copy
        n   = len(lst)
        all_numeric = n > 0 and all(isinstance(x, (int, float)) for x in lst)

        # Group A — same-length mutations (hardest to spot, most realistic)
        if all_numeric and n >= 2:
            # Wrong step: shift every element by +1 (index-off-by-one mistake)
            _try(repr([x + 1 for x in lst]), candidates)
            # Wrong step: shift every element by -1
            _try(repr([x - 1 for x in lst]), candidates)
            # Wrong slice step: elements at even indices instead of odd (or vice versa)
            alt_step = lst[::2] if lst[1::2] == lst else lst[1::2]
            if alt_step != lst:
                _try(repr(alt_step), candidates)
            # Wrong start index: start from index 0 instead of 1 (or vice versa)
            alt_start = lst[0::2] if lst == lst[1::2] else lst[0::2]
            if alt_start != lst:
                _try(repr(alt_start), candidates)

        # Group B — off-by-one length mutations (very common slicing mistake)
        if n >= 2:
            _try(repr(lst[:-1]), candidates)       # drop last element
            _try(repr(lst[1:]), candidates)        # drop first element (start=1 mistake)
        if n >= 3:
            _try(repr(lst[:-2]), candidates)       # drop last two
            _try(repr(lst[2:]), candidates)        # start=2 mistake

        # Group C — order mutations
        if n >= 2:
            _try(repr(lst[::-1]), candidates)      # full reverse (wrong step sign)
            # Rotate by 1 (student confuses index offset with rotation)
            _try(repr(lst[1:] + lst[:1]), candidates)

        # Group D — numeric mutations that preserve structure
        if all_numeric and n >= 1:
            # Multiply each element by 2 (wrong * operator in expression)
            _try(repr([x * 2 for x in lst]), candidates)
            # Integer-divide each element by 2
            _try(repr([x // 2 for x in lst]), candidates)
            # All zeros same length (common when student confuses result type)
            _try(repr([0] * n), candidates)
            # Range-based confusion: list(range(n)) instead of actual slice
            _try(repr(list(range(n))), candidates)
            # Range from 1
            _try(repr(list(range(1, n + 1))), candidates)

        # Group E — append/prepend mutations
        sentinel_elem = 0 if all_numeric else (lst[0] if lst else 0)
        _try(repr(lst + [sentinel_elem]), candidates)   # extra element appended
        _try(repr([sentinel_elem] + lst), candidates)   # extra element prepended

        # Group F — empty list (last resort, still a real distractor for empty-result questions)
        _try(repr([]), candidates)

    # ── TUPLE ─────────────────────────────────────────────────────────────────
    elif vtype is tuple:
        tup = value
        n   = len(tup)
        all_numeric = n > 0 and all(isinstance(x, (int, float)) for x in tup)

        if n >= 2:
            _try(repr(tup[:-1]), candidates)
            _try(repr(tup[1:]), candidates)
            _try(repr(tup[::-1]), candidates)
        if all_numeric and n >= 1:
            _try(repr(tuple(x + 1 for x in tup)), candidates)
            _try(repr(tuple(x - 1 for x in tup)), candidates)
            _try(repr(tuple(range(n))), candidates)
        _try(repr(()), candidates)

    # ── INT ───────────────────────────────────────────────────────────────────
    elif vtype is int and not isinstance(value, bool):
        v = value
        # Ordered: closest arithmetic mistakes first
        for candidate in [
            v + 1,           # off-by-one high
            v - 1,           # off-by-one low
            v + 2,           # off-by-two high
            v - 2,           # off-by-two low
            v * 2,           # wrong multiply
            v // 2 if v != 0 else 2,   # wrong divide (floor)
            abs(v),          # forgot negative sign
            -v if v != 0 else 1,       # sign flip
            v ** 2 if abs(v) < 20 else v + 3,  # squaring mistake (only for small values)
            0,               # zero (boundary value)
        ]:
            _try(repr(candidate), candidates)

    # ── FLOAT ─────────────────────────────────────────────────────────────────
    elif vtype is float:
        v = value
        for candidate in [
            round(v + 1.0, 10),
            round(v - 1.0, 10),
            round(v * 2.0, 10),
            round(v / 2.0, 10) if v != 0 else 1.0,
            round(v + 0.5, 10),
            round(v - 0.5, 10),
            int(v),          # truncation mistake
            round(v, 0),     # wrong rounding
            0.0,
        ]:
            _try(repr(candidate), candidates)

    # ── BOOL ──────────────────────────────────────────────────────────────────
    elif vtype is bool:
        # Only 2 bool values — realistic pads: None (None vs False confusion), 0, 1
        for alt in ("True", "False", "None", "0", "1"):
            _try(alt, candidates)

    # ── STR ───────────────────────────────────────────────────────────────────
    elif vtype is str:
        v = value
        mutations = []

        # Ordered: closest-to-correct mutations first
        if v:
            mutations += [
                repr(v[::-1]),                          # reverse (wrong step sign)
                repr(v[1:]),                            # drop first char (off-by-one start)
                repr(v[:-1]),                           # drop last char (off-by-one end)
                repr(v.upper()) if v != v.upper() else repr(v.lower()),
                repr(v.lower()) if v != v.lower() else repr(v.upper()),
                repr(v[1:-1]) if len(v) > 2 else repr(v + v[0]),  # strip both ends
                repr(v[::2]),                           # wrong step=2 slice
                repr(v[1::2]),                          # wrong step=2, offset=1
                repr(v * 2),                            # string repetition mistake
                repr(v.strip()),                        # unnecessary strip
                repr(v.title()) if v != v.title() else repr(v.swapcase()),
                repr(v.swapcase()),
            ]
        mutations.append(repr(""))    # empty string (always valid last resort)

        for c in mutations:
            _try(c, candidates)

    # ── DICT ──────────────────────────────────────────────────────────────────
    elif vtype is dict:
        keys = list(value.keys())
        n    = len(keys)

        # Remove first key (most common indexing mistake)
        if n >= 1:
            _try(repr({k: v for k, v in value.items() if k != keys[0]}), candidates)
        # Remove last key
        if n >= 2:
            _try(repr({k: v for k, v in value.items() if k != keys[-1]}), candidates)
        # Swap keys and values (if values are all hashable)
        try:
            swapped = {v: k for k, v in value.items()}
            _try(repr(swapped), candidates)
        except TypeError:
            pass
        # Keys only as a list (confusion between dict and list)
        _try(repr(list(value.keys())), candidates)
        # Values only as a list
        _try(repr(list(value.values())), candidates)
        # Empty dict
        _try(repr({}), candidates)

    # ── NoneType ─────────────────────────────────────────────────────────────
    elif value is None:
        for alt in ("False", "0", "[]", '""', "True", "{}", "()"):
            _try(alt, candidates)

    # ── UNIVERSAL SAFETY NET ──────────────────────────────────────────────────
    # Reached when: type is unrecognised (set, frozenset, complex, etc.)
    # OR when all type-specific mutations above happened to collide.
    # Ordered from most to least realistic for any Python MCQ context.
    safety_net = [
        "None", "False", "True",
        "0", "1", "-1", "2",
        "[]", "()", "{}",
        '""', "'None'",
        "0.0", "1.0",
    ]
    for sentinel in safety_net:
        if len(candidates) >= 3:
            break
        _try(sentinel, candidates)

    # ── ABSOLUTE LAST RESORT ──────────────────────────────────────────────────
    # Mathematically impossible to reach with the mutations above for any common
    # Python type, but included for correctness guarantees.
    idx = 0
    while len(candidates) < 3:
        pad = repr(f"_distractor_{idx}_")
        if _is_fresh(pad):
            candidates.append(pad)
            used.add(_normalize_str(pad))
        idx += 1

    return candidates


def build_deterministic_mcq(context: dict) -> dict:
    """
    Takes LLM-generated context (setup_code, expression, distractors,
    explanation_template), executes the expression deterministically,
    then builds and returns the final MCQ with guaranteed correct answer.

    The LLM never decides correctness — the Python interpreter does.

    If the LLM leaks the correct answer into its own distractors and fewer
    than 3 valid ones remain after filtering, replacement distractors are
    generated programmatically via _generate_fallback_distractors().
    This function NEVER raises due to distractor count.
    """
    setup_code           = context.get("setup_code", "").strip()
    expression           = context.get("expression", "").strip()
    distractors          = context.get("distractors", [])
    explanation_template = context.get("explanation_template", "")
    question             = context.get("question", "")

    if not expression:
        raise RuntimeError("Context missing 'expression' field")

    # Step 1: Execute expression deterministically
    actual_output = safe_execute(setup_code, expression)
    logger.info(f"Deterministic execution: {expression!r} → {actual_output!r}")

    # Step 2: Filter out any distractor that accidentally equals the correct answer
    # Also deduplicate distractors against each other.
    clean_distractors = []
    seen_distractors  = set()
    for d in distractors:
        d_str = str(d)
        d_norm = _normalize_str(d_str)

        # Skip if it matches the correct answer
        is_correct = False
        try:
            if ast.literal_eval(d_str) == ast.literal_eval(actual_output):
                is_correct = True
        except Exception:
            pass
        if not is_correct and d_norm == _normalize_str(actual_output):
            is_correct = True
        if is_correct:
            logger.warning(f"Distractor filtered (matches correct answer): {d_str!r}")
            continue

        # Skip inter-distractor duplicates
        if d_norm in seen_distractors:
            logger.warning(f"Distractor filtered (duplicate): {d_str!r}")
            continue

        seen_distractors.add(d_norm)
        clean_distractors.append(d_str)

    # Step 3: If fewer than 3 valid distractors remain, generate replacements
    # programmatically instead of raising. This makes the pipeline self-healing.
    needed = 3 - len(clean_distractors)
    if needed > 0:
        logger.warning(
            f"Only {len(clean_distractors)} valid distractor(s) after filtering — "
            f"generating {needed} replacement(s) programmatically"
        )
        fallbacks = _generate_fallback_distractors(actual_output, clean_distractors)
        for fb in fallbacks:
            if len(clean_distractors) >= 3:
                break
            clean_distractors.append(fb)
            logger.info(f"Fallback distractor added: {fb!r}")

        # Absolute safety net: if type-based generation somehow still falls short
        # (extremely unlikely), pad with guaranteed-unique indexed strings.
        idx = 0
        while len(clean_distractors) < 3:
            pad = repr(f"[distractor_{idx}]")
            if _normalize_str(pad) not in {_normalize_str(d) for d in clean_distractors}:
                clean_distractors.append(pad)
                logger.warning(f"Used emergency pad distractor: {pad!r}")
            idx += 1

    # Step 4: Build 4 options — 1 correct + 3 distractors — then shuffle
    all_option_texts = [actual_output] + clean_distractors[:3]
    random.shuffle(all_option_texts)

    labels  = ["A", "B", "C", "D"]
    options = [
        {
            "label":     label,
            "text":      text,
            "isCorrect": (text == actual_output),
        }
        for label, text in zip(labels, all_option_texts)
    ]

    # Step 5: Fill explanation template with the computed correct answer
    if "{CORRECT_ANSWER}" in explanation_template:
        explanation = explanation_template.replace("{CORRECT_ANSWER}", actual_output)
    else:
        explanation = f"{explanation_template} The correct answer is {actual_output}.".strip()

    return {
        "question":    question,
        "options":     options,
        "explanation": explanation,
        "difficulty":  context.get("difficulty", ""),
        "bloomLevel":  context.get("bloomLevel", "Apply"),
    }


# ============================================================================
# _run_deterministic_mcq_pipeline — for code/output-prediction MCQs
# No LLM verifier needed: the Python interpreter IS the verifier.
# ============================================================================

def _run_deterministic_mcq_pipeline(raw_text: str) -> dict:
    """
    Deterministic-first pipeline for executable/output-prediction MCQs.

    Flow:
      extract context JSON → validate fields → execute expression →
      build MCQ with computed correct answer → structural checks → return

    Correctness is guaranteed by execution, not by LLM judgment.
    LLM verifier is intentionally skipped for these MCQs.
    """
    context = extract_json(raw_text)

    # Validate required context fields
    required_fields = ["setup_code", "expression", "distractors", "explanation_template"]
    missing = [f for f in required_fields if not context.get(f)]
    if missing:
        raise RuntimeError(f"Deterministic context missing required fields: {missing}")

    if not isinstance(context.get("distractors"), list):
        raise RuntimeError("'distractors' must be a JSON array")

    # Execute and build MCQ — correctness is fully deterministic here
    try:
        final_mcq = build_deterministic_mcq(context)
    except subprocess.TimeoutExpired:
        raise RuntimeError("Deterministic execution timed out — bad expression")
    except ValueError as e:
        raise RuntimeError(f"Deterministic execution failed: {e}")

    # Structural checks (lightweight — no LLM verify needed)
    correct_options = [o for o in final_mcq["options"] if o.get("isCorrect") is True]
    if len(correct_options) != 1:
        raise RuntimeError(
            f"Deterministic build produced {len(correct_options)} correct options — "
            f"expected exactly 1"
        )

    option_texts = [o.get("text", "").strip() for o in final_mcq["options"]]
    if len(option_texts) != len(set(option_texts)):
        raise RuntimeError("Duplicate option texts in deterministic MCQ")

    # REFACTOR v7.1: raised minimum to 40 chars (same threshold as conceptual pipeline)
    if len(final_mcq.get("explanation", "").strip()) < 40:
        raise RuntimeError("Explanation too short (< 40 chars)")

    logger.info("Deterministic MCQ pipeline: success (no LLM verifier needed)")
    return final_mcq


# ============================================================================
# _run_mcq_pipeline — routes by JSON shape:
#   context JSON (has "expression" + "distractors") → deterministic pipeline
#   full MCQ JSON (has "options" + "isCorrect")     → existing LLM pipeline
# ============================================================================

def _run_mcq_pipeline(raw_text: str) -> dict:
    """
    Unified entry point. Routes to one of two sub-pipelines based on JSON shape:

    DETERMINISTIC  (code/output-prediction topics):
      Detected by: "expression" + "distractors" keys present in JSON.
      No LLM verifier. Python interpreter decides correctness.

    CONCEPTUAL  (framework/theory topics):
      Detected by: standard "options" + "isCorrect" MCQ shape.
      LLM verifier → ambiguity check → API protection → stronger structural checks.
      deterministic_validate_mcq() is NOT called here — conceptual MCQs are not
      executable so running safe_execute() on them adds no value and was a
      source of false rejections.
    """
    raw_mcq = extract_json(raw_text)

    # ── Route: deterministic pipeline ─────────────────────────────────────────
    if "expression" in raw_mcq and "distractors" in raw_mcq:
        logger.info("Routing to deterministic MCQ pipeline (code/output-prediction)")
        return _run_deterministic_mcq_pipeline(raw_text)

    # ── Route: conceptual pipeline ────────────────────────────────────────────
    logger.info("Routing to conceptual MCQ pipeline (framework/theory topic)")

    # Step 1: LLM verification
    verified_mcq = verify_mcq_with_llm(raw_mcq)

    # Step 2: Ambiguity check — reject vague opinion-based questions
    is_ambiguous, ambiguity_reason = detect_ambiguity(verified_mcq)
    if is_ambiguous:
        logger.warning(f"Conceptual MCQ rejected — ambiguity: {ambiguity_reason}")
        raise RuntimeError(f"MCQ rejected: {ambiguity_reason}")

    # Step 3: Official API protection — context-aware (App Router vs Pages Router)
    has_api_violation, api_reason = protect_official_api_logic(verified_mcq)
    if has_api_violation:
        logger.warning(f"Conceptual MCQ rejected — API protection: {api_reason}")
        raise RuntimeError(f"MCQ rejected: {api_reason}")

    # Step 4: Stronger structural validation (REFACTOR v7.1)
    # deterministic_validate_mcq() intentionally removed from conceptual branch:
    #   - Conceptual MCQs are not executable — safe_execute() always skips/fails on them
    #   - Was a source of unnecessary retries and false rejections
    #   - All correctness checking here is now structural, not execution-based
    final_mcq = verified_mcq

    # 4a: Exactly 1 correct option
    correct_options = [o for o in final_mcq.get("options", []) if o.get("isCorrect") is True]
    if len(correct_options) != 1:
        raise RuntimeError(
            f"Conceptual MCQ must have exactly 1 correct option, found {len(correct_options)}"
        )

    # 4b: No duplicate option texts (canonical comparison ignores whitespace/case)
    def _canonical(text: str) -> str:
        t = text.strip().lower()
        try:
            return repr(ast.literal_eval(t))
        except Exception:
            return re.sub(r'\s+', '', t)

    canonical_texts = [_canonical(o.get("text", "")) for o in final_mcq.get("options", [])]
    if len(canonical_texts) != len(set(canonical_texts)):
        raw_texts = [o.get("text", "").strip().lower() for o in final_mcq.get("options", [])]
        if len(raw_texts) != len(set(raw_texts)):
            raise RuntimeError("Duplicate option texts detected in conceptual MCQ")
        logger.warning("Options differ only in whitespace/formatting — allowing through")

    # 4c: Explanation length >= 40 chars
    explanation = final_mcq.get("explanation", "").strip()
    if len(explanation) < 40:
        raise RuntimeError(f"Explanation too short ({len(explanation)} chars, need >= 40)")

    # 4d: Explanation must reference the correct answer text
    # This catches explanations that are generic or don't match the marked option.
    correct_text = correct_options[0].get("text", "").strip().lower()
    # Use first 30 chars of correct option as a fingerprint to avoid false misses
    # on long code options — we only require a substring match.
    fingerprint = re.sub(r'\s+', '', correct_text[:30])
    explanation_collapsed = re.sub(r'\s+', '', explanation.lower())
    if fingerprint and len(fingerprint) >= 8 and fingerprint not in explanation_collapsed:
        logger.warning(
            f"Explanation does not reference correct answer text "
            f"(fingerprint={fingerprint!r}) — allowing through but flagging"
        )
        # Log only — do not hard-reject. Explanations legitimately paraphrase.
        # Hard-rejecting here caused unnecessary retries in v6.x (FIX 4 rationale).

    return final_mcq


# ============================================================================
# process_mcq_batch
# ============================================================================

async def process_mcq_batch():
    # REFACTOR v7.1: process_mcq_batch now delegates entirely to _run_mcq_pipeline().
    # _run_mcq_pipeline() internally routes to:
    #   - _run_deterministic_mcq_pipeline() for code/Python topics (no LLM verifier)
    #   - Conceptual pipeline for framework/theory topics (LLM verifier, no safe_execute)
    # No double-verification. No deterministic_validate_mcq() on conceptual MCQs.
    # Single retry on any pipeline failure — same prompt, full pipeline re-run.
    queue = batch_queues["mcq"]

    batch = []
    while queue and len(batch) < _batch_size_max():
        batch.append(queue.popleft())

    if not batch:
        return

    prompts, keys, ids = [], [], []
    for req_id, data, cache_key in batch:
        prompts.append(build_mcq_prompt(data))
        keys.append(cache_key)
        ids.append(req_id)

    responses, per_req_time = generate_batch(prompts)

    STATS["batches_processed"] += 1
    STATS["total_batched_requests"] += len(batch)
    STATS["avg_batch_size"] = STATS["total_batched_requests"] / STATS["batches_processed"]

    for i, text in enumerate(responses):
        primary_error = None
        final_mcq = None

        # Primary attempt: full pipeline (deterministic or conceptual, auto-routed)
        try:
            final_mcq = _run_mcq_pipeline(text)
        except Exception as e:
            primary_error = e
            logger.warning(
                f"Primary MCQ pipeline failed (item {i}, "
                f"type={'deterministic' if 'expression' in text else 'conceptual'}): {e}"
            )

        if final_mcq is not None:
            final_mcq.update({
                "generation_time_seconds": per_req_time,
                "batched": True,
                "batch_size": len(batch),
                "cache_hit": False
            })
            RESPONSE_CACHE[keys[i]] = final_mcq
            pending_results[ids[i]] = final_mcq
            continue

        # Single retry: regenerate from scratch with the same prompt and re-run pipeline.
        # Covers: ambiguity rejection, API protection rejection, structural failures,
        # execution errors, distractor leakage, bad JSON shape.
        logger.info(f"Retrying MCQ generation for item {i} (primary error: {str(primary_error)[:80]})")

        try:
            retry_prompt = build_mcq_prompt(batch[i][1])
            retry_texts, _ = generate_batch([retry_prompt])

            if not retry_texts or not retry_texts[0].strip():
                raise RuntimeError("Retry generation returned empty response")

            final_mcq = _run_mcq_pipeline(retry_texts[0])

            final_mcq.update({
                "generation_time_seconds": per_req_time,
                "batched": True,
                "batch_size": len(batch),
                "cache_hit": False
            })
            RESPONSE_CACHE[keys[i]] = final_mcq
            pending_results[ids[i]] = final_mcq
            logger.info(f"Retry succeeded for item {i}")

        except Exception as retry_exc:
            primary_msg = str(primary_error)[:120] if primary_error else "unknown"
            retry_msg   = str(retry_exc)[:120]
            logger.error(f"Retry also failed for item {i}: {retry_exc}")
            pending_results[ids[i]] = {
                "success": False,
                "error": (
                    f"MCQ generation failed after 1 retry. "
                    f"Primary: {primary_msg} | Retry: {retry_msg}"
                )
            }


# ============================================================================
# enqueue_and_wait
# ============================================================================

async def enqueue_and_wait(data: dict, cache_key: str):
    req_id = str(uuid.uuid4())
    batch_queues["mcq"].append((req_id, data, cache_key))

    if len(batch_queues["mcq"]) >= _batch_size_max():
        async with batch_locks["mcq"]:
            await process_mcq_batch()
    else:
        await asyncio.sleep(_batch_timeout())
        if req_id not in pending_results:
            async with batch_locks["mcq"]:
                if req_id not in pending_results:
                    await process_mcq_batch()

    for _ in range(600):
        if req_id in pending_results:
            result = pending_results.pop(req_id)
            if isinstance(result, Exception):
                raise HTTPException(status_code=422, detail=str(result))
            if isinstance(result, dict) and result.get("success") is False:
                raise HTTPException(status_code=422, detail=result.get("error", "MCQ generation failed"))
            return result
        await asyncio.sleep(0.05)

    raise HTTPException(status_code=504, detail="MCQ generation timeout")


# ============================================================================
# GENERIC BATCHING
# ============================================================================

async def generate_batch_with_qwen(
    prompts: List[str], max_tokens: int = 2000, temperature: float = 0.7
):
    batch_messages = []
    for prompt in prompts:
        messages = [
            {"role": "system", "content": "You are an expert assessment designer."},
            {"role": "user", "content": prompt}
        ]
        text = TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        batch_messages.append(text)

    inputs = TOKENIZER(batch_messages, return_tensors="pt", padding=True, truncation=True).to(MODEL.device)
    meter_inputs = inputs
    start_time = time.time()
    loop = asyncio.get_running_loop()
    pad = TOKENIZER.pad_token_id or TOKENIZER.eos_token_id

    def _generate_main():
        return MODEL.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=temperature,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=pad,
        )

    try:
        outputs = await loop.run_in_executor(MODEL_EXECUTOR, _generate_main)
    except torch.cuda.OutOfMemoryError:
        logger.warning(
            f"CUDA OOM on batch of {len(prompts)} — clearing cache and retrying as batch_size=1"
        )
        torch.cuda.empty_cache()
        if len(prompts) == 1:
            raise
        single_input = TOKENIZER([batch_messages[0]], return_tensors="pt", padding=True, truncation=True).to(
            MODEL.device
        )
        meter_inputs = single_input

        def _generate_single():
            return MODEL.generate(
                **single_input,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_p=0.9,
                repetition_penalty=1.1,
                pad_token_id=pad,
            )

        outputs = await loop.run_in_executor(MODEL_EXECUTOR, _generate_single)
        prompts = prompts[:1]
        logger.info("OOM recovery: processed 1 of original batch")

    try:
        input_tokens = int(meter_inputs["attention_mask"].sum(dim=-1).max().item())
        output_tokens = int(outputs.shape[1] - input_tokens)
        from backend_app.billing.metering import current_token_counts

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

    responses = []
    for output in outputs:
        response = TOKENIZER.decode(output, skip_special_tokens=True)
        response = response.split("assistant\n")[-1].strip()
        responses.append(response)

    STATS["total_generation_time"] += generation_time
    per_request_time = generation_time / len(prompts)
    logger.info(f"BATCH: {len(prompts)} requests in {generation_time:.2f}s ({per_request_time:.2f}s each)")
    return responses, generation_time, per_request_time


async def process_batch(endpoint: str, prompt_builder_func, max_tokens: int = 2000):
    queue = batch_queues[endpoint]
    if len(queue) == 0:
        return

    # AIML generates large datasets — runs alone to avoid OOM
    effective_batch_size = 1 if endpoint == "aiml" else _batch_size_max()

    # Temperature per endpoint: lower = more deterministic/structured output
    endpoint_temperature = {
        "aiml":       0.6,   # structured dataset JSON — needs consistency
        "coding":     0.6,   # structured problem JSON — needs consistency
        "sql":        0.65,  # structured SQL + schema
        "subjective": 0.7,   # some creativity needed
        "topics":     0.8,   # variety in topic suggestions
        "mcq":        0.7,   # default
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
                result.update({"generation_time_seconds": per_request_time, "batched": True,
                                "batch_size": batch_size, "cache_hit": False})
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
                    retry_result.update({"generation_time_seconds": per_request_time, "batched": True,
                                         "batch_size": batch_size, "cache_hit": False})
                    save_to_cache(cache_key, retry_result)
                    pending_results[request_id] = {"success": True, "data": retry_result}
                    logger.info(f"Retry successful for batch item {i}")
                except Exception as retry_error:
                    logger.error(f"Retry failed for batch item {i}: {retry_error}")
                    pending_results[request_id] = {
                        "success": False,
                        "error": f"Generation failed: {str(retry_error)}"
                    }
    except torch.cuda.OutOfMemoryError as oom:
        logger.error(f"CUDA OOM in batch processing — freeing cache, marking all items failed for retry")
        torch.cuda.empty_cache()
        for request_id in request_ids:
            pending_results[request_id] = {
                "success": False,
                "error": "GPU ran out of memory. Please try again with fewer simultaneous requests."
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
            else:
                raise HTTPException(status_code=500, detail=result["error"])
        await asyncio.sleep(0.1)

    raise HTTPException(status_code=504, detail="Request timeout")


# ============================================================================
# PROMPT BUILDERS (non-MCQ — unchanged)
# ============================================================================

def build_topics_prompt(request_data):
    return f"""Generate {request_data['num_topics']} assessment topics for {request_data['job_designation']}.
Skills: {', '.join(request_data['skills'])}
Experience: {request_data['experience_min']}-{request_data['experience_max']} years

RULES:
- "label" must be a SHORT topic name only (2-6 words). NOT a sentence or question.
  GOOD: "Python List Slicing", "SQL Window Functions", "React useEffect Hook"
  BAD: "Understanding how Python handles list slicing operations"
- Mix difficulty: ~30% Easy, ~50% Medium, ~20% Hard based on experience level.
- questionType must match the topic — use AIML only for ML/data science topics.
- canUseJudge0 is true only for Coding/SQL topics.

Return ONLY JSON:
{{"topics": [{{"label": "Short Topic Name", "questionType": "MCQ|Subjective|Coding|SQL|AIML|PseudoCode", "difficulty": "Easy|Medium|Hard", "canUseJudge0": true|false}}]}}"""


def build_subjective_prompt(request_data):
    return f"""
You are a strict assessment generator.

Generate ONE {request_data['difficulty']} subjective question about {request_data['topic']}.

STRICT RULES:
- Return ONLY valid JSON.
- No markdown.
- No extra explanation outside JSON.
- All fields REQUIRED.
- expectedAnswer must be detailed, at least 3-4 sentences.
- gradingCriteria: EXACTLY 4 specific, measurable criteria — NOT generic ones.
  BAD: "Correctness", "Clarity", "Understanding"
  GOOD: "Correctly explains the difference between X and Y with an example",
        "Mentions at least 2 real-world use cases", "Addresses edge case Z",
        "Uses accurate technical terminology"

MANDATORY JSON FORMAT:
{{
  "question": "Complete question text",
  "expectedAnswer": "Detailed answer explanation covering all key points",
  "gradingCriteria": [
    "Specific criterion 1 tied to the answer content",
    "Specific criterion 2 tied to the answer content",
    "Specific criterion 3 tied to the answer content",
    "Specific criterion 4 tied to the answer content"
  ],
  "difficulty": "{request_data['difficulty']}",
  "bloomLevel": "Apply"
}}

Generate now:
"""

def build_coding_prompt(request_data):
    difficulty = request_data['difficulty']
    topic      = request_data['topic']
    language   = request_data['language']
    job_role   = request_data.get('job_role', 'Software Engineer')
    exp_years  = request_data.get('experience_years', '3-5')

    difficulty_guidance = {
        "Easy": (
            "suitable for a junior developer screening. "
            "Focus on clean implementation of a single well-known algorithm or data structure. "
            "The problem should be solvable in 20-30 minutes."
        ),
        "Medium": (
            "suitable for a mid-level engineer technical interview. "
            "Require combining 2 concepts (e.g. hash map + sliding window, BFS + memoisation). "
            "Must have a naive O(n^2) solution and an optimal solution that the candidate should discover. "
            "Solvable in 30-45 minutes by a competent engineer."
        ),
        "Hard": (
            "suitable for a senior/staff engineer interview at a top tech company. "
            "Require deep algorithmic thinking: dynamic programming, graph algorithms, segment trees, "
            "or complex system-level design within a function. "
            "Must have multiple sub-problems or edge cases that trip up average candidates. "
            "Solvable in 45-60 minutes by a strong engineer."
        ),
    }.get(difficulty, "suitable for a mid-level engineer.")

    lang_starter = {
        "Python":     "def solution():\n    # your code here\n    pass",
        "JavaScript": "function solution() {\n    // your code here\n}",
        "Java":       "public class Solution {\n    public static void main(String[] args) {\n        // your code here\n    }\n}",
        "C++":        "#include <bits/stdc++.h>\nusing namespace std;\n\nint main() {\n    // your code here\n    return 0;\n}",
        "Go":         "package main\n\nimport \"fmt\"\n\nfunc solution() {\n    // your code here\n}",
        "TypeScript": "function solution(): void {\n    // your code here\n}",
    }.get(language, "// your code here")

    return f"""You are a senior engineering interviewer at a top-tier technology company.

Your task: Write ONE production-grade {difficulty} coding problem for a {job_role} with {exp_years} years of experience.
Topic area: {topic}
Language: {language}
Difficulty profile: {difficulty_guidance}

QUALITY REQUIREMENTS — every item below is MANDATORY:
1. problemStatement: Must describe a REAL-WORLD scenario (not abstract). Use concrete domain context
   such as e-commerce order processing, a ride-sharing dispatch system, log analysis pipeline,
   financial transaction deduplication, etc. The problem must feel like something from production.
2. The problem must test ALGORITHMIC THINKING, not syntax knowledge.
3. constraints: Must include realistic upper bounds (e.g. 1 <= n <= 10^6, values up to 10^9).
   At least 4 constraints. One constraint must push the candidate toward an optimal solution
   (e.g. "must run in O(n log n) or better", "memory limited to O(k)").
4. examples: At least 2 examples. Each must include a non-trivial input, the correct output,
   and a step-by-step explanation showing WHY the output is correct.
5. testCases: At least 5 test cases total.
   - 2 visible (isHidden: false): one simple, one moderate
   - 3 hidden (isHidden: true): must include edge cases:
     empty input, single element, maximum constraint values, duplicate values,
     negative numbers (if applicable), already-sorted input, etc.
6. starterCode: Must include the correct function signature with typed parameters.
   Include a brief docstring describing what the function should do.
7. The expectedComplexity field must state both time AND space complexity of the optimal solution.

STRICT OUTPUT RULES:
- Return ONLY valid JSON — no markdown fences, no explanation outside JSON.
- All string values must be plain strings (no nested objects).
- Newlines inside strings must use \n escape.
- constraints, examples, testCases must be JSON arrays.

EXACT JSON STRUCTURE:
{{
  "problemStatement": "Detailed real-world problem description as a single string",
  "inputFormat": "Precise input format description",
  "outputFormat": "Precise output format description",
  "constraints": [
    "1 <= n <= 10^6",
    "0 <= values[i] <= 10^9",
    "Solution must run in O(n log n) or better",
    "Memory usage must be O(n)"
  ],
  "examples": [
    {{
      "input": "concrete example input",
      "output": "exact expected output",
      "explanation": "Step-by-step walkthrough of why this output is correct"
    }},
    {{
      "input": "second more complex example",
      "output": "expected output",
      "explanation": "Detailed explanation"
    }}
  ],
  "testCases": [
    {{"input": "simple test", "expectedOutput": "output", "isHidden": false}},
    {{"input": "moderate test", "expectedOutput": "output", "isHidden": false}},
    {{"input": "edge case: empty", "expectedOutput": "output", "isHidden": true}},
    {{"input": "edge case: max constraint", "expectedOutput": "output", "isHidden": true}},
    {{"input": "edge case: duplicates or boundary", "expectedOutput": "output", "isHidden": true}}
  ],
  "starterCode": "{lang_starter}",
  "difficulty": "{difficulty}",
  "expectedComplexity": "Time: O(...) | Space: O(...)",
  "hints": [
    "First hint pointing toward the right approach without giving it away",
    "Second hint for candidates who are stuck"
  ]
}}

Generate the problem now:"""


def build_sql_prompt(request_data):
    difficulty = request_data['difficulty']
    topic      = request_data['topic']
    db_type    = request_data.get('database_type', 'PostgreSQL')
    job_role   = request_data.get('job_role', 'Software Engineer')
    exp_years  = request_data.get('experience_years', '3-5')

    difficulty_guidance = {
        "Easy": (
            "Test basic SELECT, WHERE, ORDER BY, GROUP BY, and simple JOINs. "
            "Schema should have 2-3 tables with obvious relationships. "
            "Solvable by a junior developer in 10-15 minutes."
        ),
        "Medium": (
            "Test multi-table JOINs across at least 3 tables, CTEs, and window functions "
            "(ROW_NUMBER, RANK, LAG/LEAD). Include a subtle requirement like ranking per group "
            "or finding the top-N per category. Solvable by a mid-level engineer in 20-30 minutes."
        ),
        "Hard": (
            "Test recursive CTEs, complex window functions (running totals, moving averages), "
            "or self-joins on hierarchical data. The naive correlated-subquery solution must be "
            "clearly worse. Solvable by a senior engineer in 30-45 minutes."
        ),
    }.get(difficulty, "Test intermediate SQL skills.")

    sql_concepts = {
        "Easy":   "Basic JOINs, GROUP BY, ORDER BY, simple aggregations",
        "Medium": "CTEs, window functions (ROW_NUMBER/RANK/LAG), multi-table JOINs, HAVING",
        "Hard":   "Recursive CTEs, advanced window functions, self-joins, complex aggregations",
    }.get(difficulty, "Intermediate SQL")

    return f"""You are a senior database engineer writing a technical interview question.

Task: Write ONE {difficulty} SQL problem for a {job_role} with {exp_years} years experience.
Topic: {topic}
Database: {db_type}
Difficulty: {difficulty_guidance}
Concepts: {sql_concepts}

RULES:
1. problemStatement: Real business scenario (e-commerce, SaaS, logistics, finance, HR). One paragraph, single string.
2. schema: 2-3 tables, realistic column names and types, foreign key relationships. Columns only — NO sample_data rows.
3. expectedQuery: The correct {db_type} solution. CRITICAL — write the entire SQL on ONE single line using spaces between clauses. Do NOT use real newlines inside the query string. Example: "SELECT u.name, COUNT(o.id) AS total FROM users u JOIN orders o ON u.id = o.user_id GROUP BY u.name ORDER BY total DESC"
4. explanation: Plain English walkthrough of the query — why each JOIN type, what each clause does. Single string.
5. alternativeApproach: One sentence describing a worse approach and why it is slower or incorrect.
6. concepts_tested: List of SQL concepts this question tests.

CRITICAL JSON RULES:
- Return ONLY a valid JSON object. No markdown. No text before or after the JSON.
- Every value must be a plain string or array — no nested objects except schema.tables.
- NO real newlines inside any string value. Use a space instead.
- NO tab characters inside any string value.
- NO control characters of any kind inside string values.

JSON FORMAT:
{{
  "problemStatement": "single string describing the real business problem",
  "schema": {{
    "database": "{db_type}",
    "tables": [
      {{
        "name": "users",
        "columns": [
          {{"name": "id", "type": "SERIAL", "primary_key": true}},
          {{"name": "email", "type": "VARCHAR(100)", "nullable": false}},
          {{"name": "created_at", "type": "TIMESTAMP"}}
        ]
      }},
      {{
        "name": "orders",
        "columns": [
          {{"name": "id", "type": "SERIAL", "primary_key": true}},
          {{"name": "user_id", "type": "INTEGER", "foreign_key": "users.id"}},
          {{"name": "amount", "type": "DECIMAL(10,2)"}},
          {{"name": "status", "type": "VARCHAR(20)"}}
        ]
      }}
    ]
  }},
  "expectedQuery": "SELECT u.email, SUM(o.amount) AS total FROM users u JOIN orders o ON u.id = o.user_id WHERE o.status = 'completed' GROUP BY u.email ORDER BY total DESC LIMIT 10",
  "explanation": "We join users to orders on user_id to combine user info with order data. We filter only completed orders using WHERE. GROUP BY aggregates totals per user. ORDER BY DESC with LIMIT 10 returns the top spenders.",
  "alternativeApproach": "A correlated subquery in SELECT would compute the sum per user but runs once per row making it O(n*m) versus the JOIN approach which is O(n log n).",
  "difficulty": "{difficulty}",
  "concepts_tested": ["{sql_concepts}"]
}}

Generate now:"""


def build_aiml_prompt(request_data):
    """
    Pass 1 prompt — model generates SCHEMA ONLY (no data rows).
    Data rows are generated programmatically in Pass 2 by generate_aiml_dataset().

    Improvements over previous version:
      - Strict anti-generic-feature enforcement with auto-reject signal
      - Concept list injected so tasks must address requested concepts
      - Difficulty-aware complexity instruction (same dataset, different depth)
      - Explicit target_type → evaluationCriteria pairing rules
      - Forbidden placeholder list prevents template echo
    """
    topic      = request_data['topic']
    difficulty = request_data['difficulty']
    concepts   = request_data.get('concepts', [])
    concepts_str = (
        f"\nCONCEPTS TO DEMONSTRATE: {', '.join(concepts)}"
        f"\n  → Each task MUST address at least one of these concepts by name."
        if concepts else ""
    )

    # Difficulty-aware complexity instruction injected into the prompt
    difficulty_instruction = {
        "Easy": (
            "DIFFICULTY = Easy: Design basic features (5-10), straightforward target, "
            "simple preprocessing (one encoding step, one scaling step). "
            "Tasks should use a single baseline model with standard metrics."
        ),
        "Medium": (
            "DIFFICULTY = Medium: Design realistic features (10-15) with mixed types, "
            "moderate class imbalance if classification, real-world missing value patterns. "
            "Tasks should compare 2 model families and include feature importance."
        ),
        "Hard": (
            "DIFFICULTY = Hard: Design complex features (12-15) including derived/interaction "
            "features, significant class imbalance, or skewed distribution. "
            "Tasks should include hyperparameter tuning, cross-validation, SHAP analysis, "
            "and a deployment consideration."
        ),
    }.get(difficulty, "DIFFICULTY = Medium: realistic features, moderate complexity.")

    return f"""You are a senior ML assessment architect. Your job is to design a SYNTHETIC dataset
schema for a machine learning problem. You generate SCHEMA ONLY — no data rows.

═══════════════════════════════════════════════════════
TOPIC    : {topic}
DIFFICULTY: {difficulty}{concepts_str}
═══════════════════════════════════════════════════════

{difficulty_instruction}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STRICT FEATURE NAMING RULES (VIOLATIONS CAUSE REJECTION)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ REQUIRED: Every feature name MUST be domain-specific and self-explanatory.
❌ FORBIDDEN: feature_0, feature_1, feature_2 ... feature_N
❌ FORBIDDEN: var_1, col_1, x_1, f1, feat1, attribute_1
❌ FORBIDDEN: any name that does not describe what it measures

Domain-specific examples (use these as a guide for YOUR topic):
  customer churn  → tenure_months, monthly_charge, num_support_calls, contract_type, has_fiber_optic
  house prices    → sqft_living, num_bedrooms, year_built, garage_spaces, neighborhood_quality
  fraud detection → transaction_amount, merchant_category, hour_of_day, distance_from_home, is_foreign
  medical         → age, bmi, blood_pressure_systolic, cholesterol_level, smoker_status, glucose_mg_dl
  loan default    → loan_amount, annual_income, debt_to_income_ratio, credit_score, employment_years
  sentiment NLP   → review_length, avg_word_length, exclamation_count, polarity_score, neg_word_ratio

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE TYPE FORMAT (EXACT)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Use EXACTLY one of:
  numerical (continuous, range: X to Y)   ← float values, NO units in string
  numerical (integer, range: X to Y)      ← int values, NO units in string
  categorical (values: A, B, C)           ← comma-separated category values

BAD:  "numerical (continuous, range: 50 to 500 GB)"    ← no units
BAD:  "numerical (continuous, range: 10 Mbps to 1000)" ← no units
GOOD: "numerical (continuous, range: 50 to 500)"
GOOD: "categorical (values: monthly, annual, bi-annual)"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TASK RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Each task MUST:
  - Reference ACTUAL feature names you defined (minimum 2 features per task)
  - Be specific to the domain of '{topic}' — NOT generic boilerplate
  - Match the difficulty level above
  - Address the requested concepts if provided

FORBIDDEN task phrases (do not use these):
  "load the dataset and inspect it"
  "plot correlations between features"
  "train at least 2 models"
  "evaluate using appropriate metrics"
  Any sentence that could apply to ANY dataset unchanged

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
EVALUATION CRITERIA RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Match evaluationCriteria to target_type EXACTLY:
  binary/multiclass classification → Accuracy, Precision, Recall, F1-Score, ROC-AUC
  continuous/regression            → RMSE, MAE, R² Score, MAPE
  clustering                       → Silhouette Score, Inertia, Davies-Bouldin Index
Do NOT mix regression and classification metrics.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT — RETURN ONLY VALID JSON
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{{
  "problemStatement": "2-3 sentence real-world problem for '{topic}': who needs this, what decision it enables, what happens without it.",
  "dataset": {{
    "description": "What this SYNTHETIC dataset represents in the real-world context of '{topic}'",
    "features": ["domain_specific_name_1", "domain_specific_name_2", "...10-15 names for {topic}"],
    "feature_types": {{
      "domain_specific_name_1": "numerical (continuous, range: 20 to 150)",
      "domain_specific_name_2": "categorical (values: option_a, option_b, option_c)"
    }},
    "target": "target_variable_name_specific_to_{topic.replace(' ','_')}",
    "target_type": "binary (0: no_event, 1: event) OR continuous OR multiclass (classes: A, B, C)",
    "class_distribution": {{"class0": 70, "class1": 30}},
    "size": "400 samples"
  }},
  "tasks": [
    "Task 1: [Specific to {topic} — name at least 2 actual feature names from above. State what domain-specific patterns to look for in the data.]",
    "Task 2: [Name which specific features need encoding by name, which need scaling by name. State whether stratification is needed.]",
    "Task 3: [Name 2-3 specific plots relevant to {topic} with actual feature names on axes — e.g. 'plot tenure_months vs churn_flag coloured by contract_type'.]",
    "Task 4: [Name 2 algorithms justified for this exact target_type and domain. State evaluation metrics. Include difficulty-appropriate depth.]",
    "Task 5: [Domain-specific business insight questions referencing actual feature names. Answer what the model reveals about the real-world problem.]"
  ],
  "preprocessing_requirements": [
    "Encode [actual_categorical_feature_name] using LabelEncoder / OneHotEncoder",
    "Scale [actual_numerical_feature_name_1] and [actual_numerical_feature_name_2] using StandardScaler",
    "Handle class imbalance / missing values / skew — specific to this dataset"
  ],
  "expectedApproach": "Name 2-3 algorithms for '{topic}' with WHY each suits this target_type, feature types, and domain.",
  "evaluationCriteria": ["metric_matched_to_target_type_1", "metric_2", "metric_3"],
  "difficulty": "{difficulty}"
}}

Generate now:"""


# ============================================================================
# AIML DATASET GENERATOR — Pass 2
# Takes schema from Pass 1, generates realistic rows programmatically.
# No GPU needed. Instant. Supports 100-500 rows reliably.
# ============================================================================

def _parse_feature_range(type_str: str):
    """
    Parse range from type strings like:
      'numerical (continuous, range: 20 to 150)'
      'numerical (continuous, range: 50 to 500 GB)'
      'numerical (continuous, range: 10 Mbps to 1000 Mbps)'
      'numerical (integer, range: 1 to 60 months)'
    Units after numbers are stripped automatically.
    """
    # Allow optional unit words (GB, Mbps, minutes, months, etc.) after numbers
    match = re.search(
        r'range[:\s]+([0-9\.\-\$k%]+)\s*[a-zA-Z/]*\s+to\s+([0-9\.\-\$k%]+)',
        type_str, re.IGNORECASE
    )
    if not match:
        return None, None
    def _clean(v):
        v = v.strip().replace('$', '').replace('%', '').replace(',', '')
        if v.lower().endswith('k'):
            return float(v[:-1]) * 1000
        return float(v)
    try:
        return _clean(match.group(1)), _clean(match.group(2))
    except:
        return None, None

def _parse_categorical_values(type_str: str):
    """Parse values from 'categorical (values: A, B, C)'"""
    match = re.search(r'values[:\s]+(.+?)(?:\)|\Z)', type_str, re.IGNORECASE)
    if not match:
        return None
    raw = match.group(1)
    values = [v.strip().strip('"\'') for v in raw.split(',') if v.strip()]
    return values if values else None

def generate_aiml_dataset(schema: dict, num_rows: int = 150) -> list:
    """
    Generate realistic dataset rows from a schema dict.
    Returns list of dicts (one per row), with target column included.
    """
    features = schema.get("features", [])
    feature_types = schema.get("feature_types", {})
    target = schema.get("target", "target")
    target_type_str = schema.get("target_type", "binary (0: no, 1: yes)")
    class_dist = schema.get("class_distribution", {})

    rng = np.random.default_rng(seed=42)

    is_binary = "binary" in target_type_str.lower()
    is_continuous = "continuous" in target_type_str.lower() or "regression" in target_type_str.lower()
    is_multiclass = "multiclass" in target_type_str.lower() or "multi-class" in target_type_str.lower()

    if is_continuous:
        t_min, t_max = _parse_feature_range(target_type_str)
        if t_min is None:
            t_min, t_max = 0.0, 100.0
        target_values = rng.uniform(t_min, t_max, num_rows).round(2).tolist()
    elif is_multiclass:
        match = re.search(r'classes[:\s]+(.+?)(?:\)|\Z)', target_type_str, re.IGNORECASE)
        if match:
            classes = [c.strip() for c in match.group(1).split(',')]
        else:
            classes = list(class_dist.keys()) if class_dist else ["A", "B", "C"]
        if class_dist:
            total_pct = sum(class_dist.values())
            counts = {c: max(1, int(num_rows * v / total_pct)) for c, v in class_dist.items()}
        else:
            per_class = num_rows // len(classes)
            counts = {c: per_class for c in classes}
        target_list = []
        for cls, cnt in counts.items():
            target_list.extend([cls] * cnt)
        while len(target_list) < num_rows:
            target_list.append(classes[0])
        target_values = target_list[:num_rows]
        rng.shuffle(target_values)
    else:
        # Binary
        label_match = re.search(r'0[:\s]+(\w+).*?1[:\s]+(\w+)', target_type_str)
        label0 = label_match.group(1) if label_match else "0"
        label1 = label_match.group(2) if label_match else "1"
        keys = list(class_dist.keys())
        vals = list(class_dist.values())
        if len(vals) >= 2:
            total = sum(vals)
            n_class1 = max(1, int(num_rows * vals[-1] / total))
        else:
            n_class1 = num_rows // 4
        n_class0 = num_rows - n_class1
        target_values = [0] * n_class0 + [1] * n_class1
        rng.shuffle(target_values)

    rows = []
    for row_idx in range(num_rows):
        row = {}
        target_val = target_values[row_idx]
        is_minority_row = (target_val == 1) if is_binary else False

        for feat in features:
            type_str = feature_types.get(feat, "numerical (continuous, range: 0 to 100)")
            type_lower = type_str.lower()

            if "categorical" in type_lower:
                cats = _parse_categorical_values(type_str)
                if not cats:
                    cats = ["A", "B", "C"]
                if is_minority_row and len(cats) >= 2:
                    weights = [0.3] + [0.7 / (len(cats) - 1)] * (len(cats) - 1)
                    row[feat] = str(rng.choice(cats, p=weights))
                else:
                    row[feat] = str(rng.choice(cats))
            elif "integer" in type_lower:
                lo, hi = _parse_feature_range(type_str)
                if lo is None:
                    lo, hi = 0, 10
                lo, hi = int(lo), int(hi)
                if is_minority_row:
                    val = int(rng.integers(max(lo, int((lo + hi) * 0.5)), hi + 1))
                else:
                    val = int(rng.integers(lo, hi + 1))
                row[feat] = val
            else:
                lo, hi = _parse_feature_range(type_str)
                if lo is None:
                    lo, hi = 0.0, 100.0
                base = rng.uniform(lo, hi)
                noise = rng.normal(0, (hi - lo) * 0.03)
                val = float(np.clip(base + noise, lo, hi))
                row[feat] = round(val, 2)

        row[target] = target_val
        rows.append(row)

    logger.info(f"Generated {len(rows)} dataset rows for {len(features)} features")
    return rows


# ============================================================================
# AIML VALIDATION (unchanged)
# ============================================================================

def validate_aiml_response(obj: dict) -> None:
    """
    Structural validation — checks dataset schema integrity.
    """
    if "dataset" not in obj:
        return

    dataset  = obj["dataset"]
    target   = dataset.get("target")
    features = dataset.get("features", [])

    if not target:
        raise ValueError("Target variable not specified")
    if not features:
        raise ValueError("Features list is empty")
    if target in features:
        raise ValueError(f"DATA LEAKAGE: Target '{target}' in features list")

    if "data" not in dataset or not dataset["data"]:
        logger.info("AIML validation: no data array (Pass 2 will generate rows) — schema checks passed")
        return

    data_rows = dataset["data"]
    if not isinstance(data_rows, list) or len(data_rows) == 0:
        logger.warning("Dataset data array is empty — Pass 2 will fill it")
        return

    first_row = data_rows[0]
    if not isinstance(first_row, dict):
        raise ValueError("First data row is not a dict")
    if target in first_row:
        raise ValueError(f"DATA LEAKAGE: Target '{target}' in data rows")

    expected_features = set(features)
    actual_features   = set(first_row.keys())
    if expected_features != actual_features:
        missing = expected_features - actual_features
        extra   = actual_features   - expected_features
        logger.warning(
            f"Feature mismatch — missing: {missing}, extra: {extra} — "
            f"reconciling features list to match actual data columns"
        )
        dataset["features"] = list(actual_features)
        features = dataset["features"]

    last_row = data_rows[-1]
    if not isinstance(last_row, dict) or len(last_row) == 0:
        raise ValueError("Last data row is empty — likely truncated JSON")
    if len(last_row) < len(features):
        raise ValueError(f"Last row incomplete: {len(last_row)} fields, expected {len(features)}")

    logger.info(f"AIML validation PASSED: {len(data_rows)} rows, {len(features)} features")


def validate_and_fix_aiml_response(obj: dict) -> dict:
    """
    Auto-fix layer — removes target from features if leaked, then validates.
    """
    if "dataset" not in obj:
        return obj

    dataset  = obj["dataset"]
    target   = dataset.get("target")
    features = dataset.get("features", [])

    if target and target in features:
        logger.warning(f"AUTO-FIX: Removing '{target}' from features")
        dataset["features"] = [f for f in features if f != target]

    if target and "data" in dataset:
        for row in dataset["data"]:
            if isinstance(row, dict) and target in row:
                del row[target]

    validate_aiml_response(obj)
    return obj


def validate_aiml_output(
    result: dict,
    topic: str,
    concepts: list,
    difficulty: str,
    matched_dataset: dict | None = None,
) -> tuple:
    """
    Semantic validation layer — runs AFTER LLM generation.

    Checks:
      1. Problem statement is non-trivial and exists
      2. Tasks reference actual feature names (not generic placeholders)
      3. Difficulty field matches what was requested — auto-corrects if not
      4. No generic feature names (feature_0, feature_1, ...) leaked through
      5. evaluationCriteria match target_type — auto-corrects if not
      6. Concepts are reflected in at least one task
      7. If library dataset was matched, problem domain is consistent

    Returns (is_valid: bool, issues: list[str])
    """
    issues = []
    topic_lower = topic.lower()

    # Check 1: problem statement
    stmt = result.get("problemStatement", "")
    if not stmt or len(stmt) < 50:
        issues.append("problemStatement missing or too short (< 50 chars)")

    # Check 2: difficulty auto-correct
    result_diff = result.get("difficulty", "").lower()
    if result_diff and result_diff != difficulty.lower():
        logger.warning(
            f"Difficulty mismatch: requested='{difficulty}' returned='{result_diff}' — auto-correcting"
        )
        result["difficulty"] = difficulty

    # Check 3: no generic feature names
    features = result.get("dataset", {}).get("features", [])
    generic_pattern = re.compile(r'^(feature_?\d+|var_?\d+|col_?\d+|x_?\d+|f\d+)$', re.IGNORECASE)
    generic_features = [f for f in features if generic_pattern.match(f)]
    if generic_features:
        issues.append(
            f"Generic feature names detected: {generic_features[:5]}. "
            f"Features must be domain-specific for topic='{topic}'"
        )

    # Check 4: tasks reference feature names
    tasks = result.get("tasks", [])
    if features and tasks:
        tasks_text = " ".join(tasks).lower()
        matches    = [f for f in features if f.lower() in tasks_text]
        if len(matches) < 2:
            issues.append(
                f"Tasks do not reference dataset features. "
                f"Only {len(matches)}/{len(features)} features mentioned."
            )

    # Check 5: evaluationCriteria match target_type — auto-correct
    target_type   = result.get("dataset", {}).get("target_type", "").lower()
    eval_criteria = [c.lower() for c in result.get("evaluationCriteria", [])]
    if target_type and eval_criteria:
        is_regression_type        = "continuous" in target_type
        regression_metrics        = {"rmse", "mae", "r²", "r2", "mse", "mape"}
        classification_metrics    = {"accuracy", "f1", "precision", "recall", "roc", "auc"}
        has_regression_metric     = any(m in " ".join(eval_criteria) for m in regression_metrics)
        has_classification_metric = any(m in " ".join(eval_criteria) for m in classification_metrics)

        if is_regression_type and not has_regression_metric:
            logger.warning("evaluationCriteria mismatch: continuous target but classification metrics — auto-fixing")
            result["evaluationCriteria"] = [
                "Root Mean Squared Error (RMSE)", "Mean Absolute Error (MAE)", "R² Score"
            ]
        elif not is_regression_type and not has_classification_metric and has_regression_metric:
            logger.warning("evaluationCriteria mismatch: classification target but regression metrics — auto-fixing")
            result["evaluationCriteria"] = [
                "Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC Score"
            ]

    # Check 6: concept coverage in tasks
    if concepts and tasks:
        tasks_text_lower = " ".join(tasks).lower()
        uncovered = []
        for concept in concepts:
            concept_words = [w for w in concept.lower().split() if len(w) > 3]
            if concept_words and not any(w in tasks_text_lower for w in concept_words):
                uncovered.append(concept)
        if len(uncovered) > max(1, len(concepts) // 2):
            issues.append(
                f"Concepts not reflected in tasks: {uncovered}. "
                f"Tasks should address the requested concepts."
            )

    # Check 7: library dataset domain consistency
    if matched_dataset:
        ds_domain  = matched_dataset.get("domain", "").lower()
        ds_name    = matched_dataset.get("name", "").lower()
        stmt_lower = stmt.lower()
        domain_words = set(ds_domain.replace("/", " ").split())
        name_words   = set(w for w in ds_name.split() if len(w) > 3)
        combined     = domain_words | name_words
        if combined and not any(w in stmt_lower for w in combined):
            issues.append(
                f"Problem statement does not reflect dataset domain '{ds_domain}' "
                f"or name '{matched_dataset.get('name')}'. "
                f"The problem must be grounded in the actual dataset context."
            )

    is_valid = len(issues) == 0
    if not is_valid:
        logger.warning(
            f"AIML output validation FAILED for topic='{topic}': " + " | ".join(issues)
        )
    else:
        logger.info(f"AIML output validation PASSED for topic='{topic}'")

    return is_valid, issues


def calculate_aiml_token_limit(request_data: dict) -> int:
    # Generous limits — AIML problems with 80-150 rows need significant tokens.
    # Easy gets 10k, Medium 14k, Hard 16k. No artificial cap.
    difficulty = request_data.get('difficulty', 'medium').lower()
    return {'easy': 10000, 'medium': 14000, 'hard': 16000}.get(difficulty, 14000)



# ============================================================================
# ASYNC JOB QUEUE SYSTEM
# Each endpoint now returns a job_id immediately.
# The client polls GET /api/v1/job/{job_id} until status = "complete" | "failed".
# This prevents HTTP timeouts on slow generations (90-180s on 8GB GPU).
# ============================================================================

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
    """
    Background worker — runs the full generation loop for any endpoint.
    Stores result in JOB_STORE when done. All existing batch/cache/retry
    logic is preserved — this is just a wrapper that fires in the background.
    """
    t0 = time.time()
    JOB_STORE[job_id] = {"status": "processing", "result": None, "error": None}
    try:
        # ── TOPICS: single call, result is already fully shaped {"topics":[...], ...}
        # Do NOT loop or wrap in a list — return directly.
        if endpoint == "topics":
            item_data = {k: v for k, v in request_data.items() if k not in ("num_questions",)}
            cache_key = generate_cache_key("topics", item_data)
            if use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    JOB_STORE[job_id] = {"status": "complete", "result": cached, "error": None}
                    logger.info(f"Job {job_id[:8]} topics — cache hit")
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
            JOB_STORE[job_id] = {"status": "complete", "result": result, "error": None}
            logger.info(f"Job {job_id[:8]} complete — topics generated")
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=usage_meta,
                route=route,
                cache_hit=False,
                latency_ms=(time.time() - t0) * 1000,
                status="success",
            )
            return

        # ── ALL OTHER ENDPOINTS: loop and collect items into a list ───────────
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
            "mcq":        "questions",
            "subjective": "questions",
            "coding":     "coding_problems",
            "sql":        "sql_problems",
            "aiml":       "aiml_problems",
        }
        result_key = key_map.get(endpoint, "items")
        JOB_STORE[job_id] = {
            "status": "complete",
            "result": {
                result_key: all_items,
                "generation_time_seconds": round(total_time, 3),
                "cache_hit": any_cache_hit,
                "batched": True,
                "batch_size": num_q,
            },
            "error": None,
        }
        logger.info(f"Job {job_id[:8]} complete — {num_q} {endpoint} item(s) generated")
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
        JOB_STORE[job_id] = {"status": "failed", "result": None, "error": str(e)}
        _emit_usage_metering(
            job_id=job_id,
            usage_meta=usage_meta,
            route=route,
            cache_hit=False,
            latency_ms=(time.time() - t0) * 1000,
            status="error",
            error_detail=str(e)[:500],
        )


@app.get("/api/v1/job/{job_id}")
async def poll_job(job_id: str):
    """
    Poll the status of an async generation job.
    Returns:
      {"status": "pending"}                              — not started yet
      {"status": "processing"}                           — GPU is generating
      {"status": "complete", "result": {...}}            — done, result included
      {"status": "failed",   "error": "..."}            — generation failed
    """
    if job_id not in JOB_STORE:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found or expired")
    return JOB_STORE[job_id]

# ============================================================================
# STARTUP + INFO ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    return {
        "service": "Qwen API - Production Hardened",
        "version": "9.0.0",
        "v8_changes": [
            "FEAT: All endpoints now support num_questions (int, default=1) for bulk generation",
            "FEAT: All endpoints return list-based batch responses (questions/coding_problems/sql_problems/aiml_problems)",
            "FEAT: Per-item cache keys include question_index to prevent identical cached results across slots",
            "FEAT: POST /api/v1/clear-cache endpoint to flush entire response cache on demand",
            "FEAT: use_cache=False bypasses cache per-request, forcing fresh generation for every item",
            "FEAT: TopicBatchResponse / MCQBatchResponse / SubjectiveBatchResponse / CodingBatchResponse / SQLBatchResponse / AIMLBatchResponse models added",
        ],
        "v7_changes": [
            "FIX ROUTING: _CODE_TOPIC_KEYWORDS narrowed to execution-specific signals only",
        ],
        "v6_fixes": [
            "FIX1: verify_mcq_with_llm now raises on rejected:true from verifier",
            "FIX2: safe_execute uses minimal PATH env instead of env={} (fixes Linux crash)",
            "FIX3: Added from-import pattern to blocked code patterns",
            "FIX4: explanation_mismatch changed to skip (not reject) to avoid false retries",
            "FIX5: extract_json only calls AIML validation when dataset key present",
            "FIX6: build_mcq_prompt has domain-aware rules for 12+ tech domains",
        ],
    }


@app.get("/health")
async def health_check():
    active_jobs = sum(1 for v in JOB_STORE.values() if v.get("status") in ("pending", "processing"))
    return {
        "status": "healthy",
        "model_loaded": MODEL is not None,
        "memory_gb": torch.cuda.memory_allocated() / 1024**3 if torch.cuda.is_available() else 0,
        "queue_sizes": {e: len(q) for e, q in batch_queues.items()},
        "active_jobs": active_jobs,
        "total_jobs_in_store": len(JOB_STORE)
    }


@app.get("/stats")
async def get_stats():
    cache_hit_rate = (STATS["cache_hits"] / max(1, STATS["cache_hits"] + STATS["cache_misses"])) * 100
    return {
        "total_requests": STATS["total_requests"],
        "cache_hit_rate_percent": round(cache_hit_rate, 2),
        "requests_by_endpoint": STATS["requests_by_endpoint"],
        "batches_processed": STATS["batches_processed"],
        "avg_batch_size": round(STATS["avg_batch_size"], 2),
        "errors": STATS["errors"]
    }


# ============================================================================
# ENDPOINTS
# ============================================================================

@app.post("/api/v1/generate-topics")
async def generate_topics(body: TopicGenerationRequest, http_request: Request):
    """
    Topics: single model call with num_topics = num_questions.
    Returns job_id immediately — client polls /api/v1/job/{job_id}.
    """
    update_stats("topics")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    # Topics use a single call — pass num_topics directly; loop runs once
    item_data = {**data, "num_topics": num_q}
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}

    # Check cache before launching background task
    cache_key = generate_cache_key("topics", item_data)
    if body.use_cache:
        cached = get_from_cache(cache_key)
        if cached:
            cached["cache_hit"] = True
            JOB_STORE[job_id] = {"status": "complete", "result": cached, "error": None}
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


@app.post("/api/v1/generate-mcq")
async def generate_mcq(body: MCQGenerationRequest, http_request: Request):
    update_stats("mcq")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}

    async def _mcq_task():
        t0 = time.time()
        JOB_STORE[job_id]["status"] = "processing"
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
            JOB_STORE[job_id] = {
                "status": "complete",
                "result": {
                    "questions": all_questions,
                    "generation_time_seconds": round(total_time, 3),
                    "cache_hit": any_cache_hit,
                    "batched": True,
                    "batch_size": num_q,
                },
                "error": None,
            }
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
            JOB_STORE[job_id] = {"status": "failed", "result": None, "error": str(e)}
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


@app.post("/api/v1/generate-subjective")
async def generate_subjective(body: SubjectiveGenerationRequest, http_request: Request):
    update_stats("subjective")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}
    asyncio.create_task(
        _run_generation_task(
            job_id,
            "subjective",
            data,
            build_subjective_prompt,
            3000,
            num_q,
            body.use_cache,
            usage_meta=um,
            route="generate-subjective",
        )
    )
    return {"job_id": job_id, "status": "pending"}


@app.post("/api/v1/generate-coding")
async def generate_coding(body: CodingGenerationRequest, http_request: Request):
    update_stats("coding")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}
    asyncio.create_task(
        _run_generation_task(
            job_id,
            "coding",
            data,
            build_coding_prompt,
            4000,
            num_q,
            body.use_cache,
            usage_meta=um,
            route="generate-coding",
        )
    )
    return {"job_id": job_id, "status": "pending"}


@app.post("/api/v1/generate-sql")
async def generate_sql(body: SQLGenerationRequest, http_request: Request):
    update_stats("sql")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    num_q = max(1, body.num_questions)
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}
    asyncio.create_task(
        _run_generation_task(
            job_id,
            "sql",
            data,
            build_sql_prompt,
            3500,
            num_q,
            body.use_cache,
            usage_meta=um,
            route="generate-sql",
        )
    )
    return {"job_id": job_id, "status": "pending"}


@app.post("/api/v1/generate-aiml")
async def generate_aiml(body: AIMLGenerationRequest, http_request: Request):
    update_stats("aiml")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()
    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}

    async def _aiml_task():
        t0 = time.time()
        JOB_STORE[job_id]["status"] = "processing"
        try:
            item_data = {k: v for k, v in data.items()}
            cache_key = generate_cache_key("aiml", item_data)

            if body.use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    JOB_STORE[job_id] = {
                        "status": "complete",
                        "result": {"aiml_problems": [cached], "generation_time_seconds": 0, "cache_hit": True, "batched": False, "batch_size": 1},
                        "error": None,
                    }
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml",
                        cache_hit=True,
                        latency_ms=(time.time() - t0) * 1000,
                        status="success",
                    )
                    return

            # ── Pass 1: Model generates schema (no data rows) ─────────────
            token_limit = calculate_aiml_token_limit(item_data)
            result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)

            # ── Pass 2: Python generates dataset rows from schema ──────────
            difficulty = item_data.get("difficulty", "Medium").lower()
            num_rows = {"easy": 300, "medium": 400, "hard": 500}.get(difficulty, 400)

            try:
                dataset_schema = result.get("dataset", {})
                generated_rows = generate_aiml_dataset(dataset_schema, num_rows=num_rows)
                result["dataset"]["data"] = generated_rows
                result["dataset"]["size"] = f"{len(generated_rows)} samples"
                logger.info(f"Pass 2 complete: {len(generated_rows)} rows generated")
            except Exception as gen_err:
                logger.error(f"Pass 2 dataset generation failed: {gen_err}")
                result["dataset"]["data"] = []
                result["dataset"]["size"] = "0 samples (generation failed)"

            # ── Fallback for fields the model may return empty ─────────────
            target_type = result.get("dataset", {}).get("target_type", "")
            is_regression = "continuous" in target_type.lower()

            if not result.get("preprocessing_requirements") or result["preprocessing_requirements"] == [""]:
                feature_types = result.get("dataset", {}).get("feature_types", {})
                cat_feats = [f for f, t in feature_types.items() if "categorical" in t.lower()]
                num_feats = [f for f, t in feature_types.items() if "numerical" in t.lower()]
                steps = []
                if cat_feats:
                    steps.append(f"Encode categorical features ({', '.join(cat_feats[:2])}) using LabelEncoder or OneHotEncoder.")
                if num_feats:
                    steps.append(f"Normalize numerical features ({', '.join(num_feats[:2])}) using MinMaxScaler or StandardScaler.")
                steps.append("Split dataset 80/20 into training and test sets using train_test_split.")
                if not is_regression:
                    steps.append("Check for class imbalance — apply SMOTE or use class_weight='balanced' if needed.")
                result["preprocessing_requirements"] = steps

            if not result.get("expectedApproach") or len(result.get("expectedApproach", "")) < 20:
                if is_regression:
                    result["expectedApproach"] = "Use Linear Regression as a baseline for interpretability. Also train Random Forest Regressor which handles non-linear relationships well. Compare using RMSE and R² score."
                else:
                    result["expectedApproach"] = "Use Logistic Regression as a baseline for interpretability. Also train Random Forest Classifier which handles non-linear feature interactions. Compare using F1-Score and ROC-AUC."

            if not result.get("evaluationCriteria") or result["evaluationCriteria"] == [""]:
                if is_regression:
                    result["evaluationCriteria"] = ["Mean Absolute Error (MAE)", "Root Mean Squared Error (RMSE)", "R² Score", "Mean Absolute Percentage Error (MAPE)"]
                else:
                    result["evaluationCriteria"] = ["Accuracy", "Precision", "Recall", "F1-Score", "ROC-AUC Score"]

            result["dataset_strategy"] = "synthetic"

            # ── Semantic validation of generated output ────────────────────
            topic_req     = item_data.get("topic", "")
            concepts_req  = item_data.get("concepts", [])
            difficulty_req = item_data.get("difficulty", "Medium")
            _is_valid, _issues = validate_aiml_output(
                result, topic_req, concepts_req, difficulty_req, matched_dataset=None
            )
            if not _is_valid:
                logger.warning(
                    f"Synthetic AIML output has quality issues — returning with warnings: {_issues}"
                )
                result["validation_warnings"] = _issues
            # ──────────────────────────────────────────────────────────────

            save_to_cache(cache_key, result)

            JOB_STORE[job_id] = {
                "status": "complete",
                "result": {
                    "aiml_problems": [result],
                    "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3),
                    "cache_hit": False,
                    "batched": False,
                    "batch_size": 1,
                },
                "error": None,
            }
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
            JOB_STORE[job_id] = {"status": "failed", "result": None, "error": str(e)}
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


@app.post("/api/v1/clear-cache")
async def clear_cache():
    """
    Clears the entire in-memory response cache.
    Use this when you want to force fresh generation for all subsequent requests,
    regardless of whether use_cache=True is set on individual requests.
    """
    cleared_count = len(RESPONSE_CACHE)
    RESPONSE_CACHE.clear()
    logger.info(f"Cache cleared: {cleared_count} entries removed")
    return {
        "status": "cache cleared",
        "entries_removed": cleared_count,
        "message": f"Successfully cleared {cleared_count} cached response(s)"
    }


# ============================================================================
# DSA ENRICHMENT ENDPOINT v3.0 — DATASET-DRIVEN
#
# Test cases come directly from LeetCodeDataset-train.jsonl
#   input_output field → structured test cases (100% accurate)
#   first 3 → public_testcases
#   next 5  → hidden_testcases
#
# Qwen generates ONLY:
#   function_signature (name, parameters, return_type)
#   starter_code for 10 languages
# ============================================================================

def _classify_testcase(raw_input: str) -> str:
    """
    Classifies a test case as 'simple' or 'edge' by analyzing the input string.

    Simple indicators:
      - Small arrays (length < 8 elements)
      - Small numbers (all values < 1000)
      - No negatives
      - Short strings (length < 10)

    Edge case indicators:
      - Large arrays (>= 8 elements)
      - Large numbers (>= 10^6)
      - Negative numbers
      - Empty arrays/strings
      - Single element arrays
      - All same elements
      - Very long strings
    """
    import re

    # Check for large numbers
    numbers = re.findall(r'-?\d+', raw_input)
    if numbers:
        vals = [int(n) for n in numbers]
        if any(abs(v) >= 1000000 for v in vals):
            return "edge"
        if any(v < 0 for v in vals):
            return "edge"

    # Check for large arrays
    arrays = re.findall(r'\[([^\[\]]*)\]', raw_input)
    for arr in arrays:
        elements = [e.strip() for e in arr.split(',') if e.strip()]
        if len(elements) == 0:
            return "edge"   # empty array
        if len(elements) == 1:
            return "edge"   # single element
        if len(elements) >= 8:
            return "edge"   # large array
        # All same elements
        if len(set(elements)) == 1 and len(elements) > 1:
            return "edge"

    # Check for empty strings
    if '""' in raw_input or "''" in raw_input:
        return "edge"

    # Check for long strings
    strings = re.findall(r'"([^"]*)"', raw_input)
    for s in strings:
        if len(s) >= 10:
            return "edge"

    return "simple"


def _parse_input_output(input_output: list) -> tuple:
    """
    Parses input_output field from LeetCodeDataset.
    Each item: {"input": "nums = [2,7,11,15], target = 9", "output": "[0, 1]"}

    Strategy:
      - Classify each test case as 'simple' or 'edge' by analyzing input
      - Take first 4 simple ones → public_testcases
      - Take first 8 edge/remaining ones → hidden_testcases
      - Fallback: if not enough simple ones, use position (first 4 = public)

    Returns (public_testcases, hidden_testcases).
    """
    all_cases = []

    for item in input_output:
        raw_input  = (item.get("input") or "").strip()
        raw_output = (item.get("output") or "").strip()

        if not raw_input or not raw_output:
            continue

        # Try to parse expected_output as JSON value
        try:
            expected_output = json.loads(raw_output)
        except Exception:
            expected_output = raw_output

        case_type = _classify_testcase(raw_input)

        all_cases.append({
            "input_raw":       raw_input,
            "expected_output": expected_output,
            "case_type":       case_type,
        })

    # Split into simple and edge
    simple_cases = [c for c in all_cases if c["case_type"] == "simple"]
    edge_cases   = [c for c in all_cases if c["case_type"] == "edge"]

    # If not enough simple cases, fall back to positional split
    if len(simple_cases) < 2:
        simple_cases = all_cases[:4]
        edge_cases   = all_cases[4:]

    # Build public — first 4 simple
    public_testcases = []
    for c in simple_cases[:4]:
        public_testcases.append({
            "input_raw":       c["input_raw"],
            "expected_output": c["expected_output"],
            "is_hidden":       False,
            "case_type":       "simple"
        })

    # Build hidden — first 8 edge cases
    # Fill remaining slots from simple if not enough edge cases
    hidden_pool = edge_cases + [c for c in simple_cases[4:]]
    hidden_testcases = []
    for c in hidden_pool[:8]:
        hidden_testcases.append({
            "input_raw":       c["input_raw"],
            "expected_output": c["expected_output"],
            "is_hidden":       True,
            "case_type":       "edge"
        })

    return public_testcases, hidden_testcases


def _build_starter_prompt(problem: dict) -> str:
    """
    Minimal prompt — only asks Qwen for function_signature + starter_code.
    Test cases already extracted from dataset.
    """
    title        = problem.get("title", "")
    difficulty   = problem.get("difficulty", "Medium")
    topics       = ", ".join(problem.get("tags", problem.get("topics", [])))
    description  = problem.get("problem_description", problem.get("description", ""))[:400]
    starter_code = problem.get("starter_code", "")
    entry_point  = problem.get("entry_point", "")

    # Extract function name from entry_point e.g. "Solution().twoSum" → "twoSum"
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
   Extract parameter names + types from the Python starter code.
   Use Python types: List[int], List[str], str, int, bool, float,
   Optional[TreeNode], Optional[ListNode], List[List[int]], etc.
2. starter_code: use EXACT function name for ALL 10 languages.
   Match parameter types correctly for each language.
3. Return ONLY valid JSON. No markdown, no explanation.

Generate now:"""


@app.post("/api/v1/enrich-dsa")
async def enrich_dsa(http_request: Request, problem: dict = Body(...)):
    """
    Dataset-driven DSA enrichment v3.0.
    Test cases come from input_output field (100% accurate from LeetCodeDataset).
    Qwen generates only function_signature + starter_code for 10 languages.
    """
    um = bind_usage_meta_from_request(http_request)
    rid = str(uuid.uuid4())
    t0 = time.perf_counter()
    title        = problem.get("title", problem.get("task_id", ""))
    input_output = problem.get("input_output", [])

    logger.info(f"DSA enrich v3: {title}")

    # ── Step 1: Parse test cases from dataset (no Qwen needed) ───────────────
    public_testcases, hidden_testcases = _parse_input_output(input_output)

    if not public_testcases and not hidden_testcases:
        raise HTTPException(
            status_code=500,
            detail="No input_output data found — cannot generate test cases"
        )

    # ── Step 2: Ask Qwen for function_signature + starter_code only ──────────
    prompt = _build_starter_prompt(problem)

    try:
        messages = [
            {"role": "system", "content": "You are an expert software engineer. Return only valid JSON."},
            {"role": "user",   "content": prompt}
        ]
        text = TOKENIZER.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs_tok = TOKENIZER(text, return_tensors="pt").to(MODEL.device)
        output = MODEL.generate(
            **inputs_tok,
            max_new_tokens=2000,
            temperature=0.2,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=TOKENIZER.eos_token_id
        )
        decoded = TOKENIZER.decode(output[0], skip_special_tokens=True)
        decoded = decoded.split("assistant")[-1].strip()
        result  = extract_json(decoded)

    except Exception as e:
        logger.error(f"Qwen starter generation failed for '{title}': {e}")
        raise HTTPException(status_code=500, detail=str(e))

    # Validate required fields
    for field in ["function_signature", "starter_code"]:
        if field not in result:
            raise HTTPException(status_code=500, detail=f"Missing field: {field}")

    logger.info(
        f"Enrichment done: {title} | "
        f"public={len(public_testcases)}, hidden={len(hidden_testcases)}, "
        f"langs={len(result.get('starter_code', {}))}"
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
        "pipeline":           "dataset_driven",
        "test_case_source":   "leetcode_dataset",
        "function_signature": result["function_signature"],
        "public_testcases":   public_testcases,
        "hidden_testcases":   hidden_testcases,
        "starter_code":       result["starter_code"],
    }




# ============================================================================
# DSA QUESTION GENERATION ENDPOINT — FAISS RAG
# Uses FAISS vector search to find semantically similar problems.
# Falls back to keyword matching if FAISS index not available.
# ============================================================================

import os as _os
import numpy as _np

def _dsa_enriched_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().dsa_enriched_path)


def _dsa_faiss_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().dsa_faiss_path)


def _dsa_metadata_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().dsa_metadata_path)

_dsa_enriched_cache  = None
_dsa_faiss_index     = None
_dsa_metadata_cache  = None
_dsa_embed_model     = None


def _load_dsa_enriched():
    global _dsa_enriched_cache
    if _dsa_enriched_cache is None:
        p = _dsa_enriched_path()
        if not _os.path.exists(p):
            raise FileNotFoundError(f"dsa_enriched.json not found at {p}")
        with open(p, encoding="utf-8") as f:
            _dsa_enriched_cache = json.load(f)
        logger.info(f"Loaded {len(_dsa_enriched_cache)} problems from dsa_enriched.json")
    return _dsa_enriched_cache


def _load_faiss_index():
    global _dsa_faiss_index, _dsa_metadata_cache, _dsa_embed_model
    if _dsa_faiss_index is None:
        if not _os.path.exists(_dsa_faiss_path()):
            logger.warning("FAISS index not found — falling back to keyword matching")
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

            logger.info(f"FAISS ready: {_dsa_faiss_index.ntotal} vectors")
            return True
        except Exception as e:
            logger.warning(f"FAISS load failed: {e} — falling back to keyword matching")
            return False
    return True


def _faiss_search(query: str, difficulty: str, top_k: int = 20) -> list:
    """
    Searches FAISS index for semantically similar problems.
    Filters by difficulty after search.
    Returns list of matching problems from enriched dataset.
    """
    problems = _load_dsa_enriched()

    # Embed the query
    query_vec = _dsa_embed_model.encode(
        [query],
        convert_to_numpy=True,
        normalize_embeddings=True
    ).astype(_np.float32)

    # Search FAISS — get top_k*3 to allow for difficulty filtering
    scores, indices = _dsa_faiss_index.search(query_vec, top_k * 3)

    matched = []
    for idx in indices[0]:
        if idx < 0 or idx >= len(_dsa_metadata_cache):
            continue
        meta = _dsa_metadata_cache[idx]
        if meta.get("difficulty", "").lower() != difficulty.lower():
            continue
        # Get full problem from enriched dataset
        if idx < len(problems):
            matched.append(problems[idx])
        if len(matched) >= top_k:
            break

    return matched


def _keyword_filter(problems: list, difficulty: str, topic: str, concepts: list) -> list:
    """Fallback keyword matching when FAISS is not available."""
    difficulty_lower = difficulty.lower()
    keywords = [topic.lower()] + [c.lower() for c in concepts]

    matched = []
    for p in problems:
        if p.get("difficulty", "").lower() != difficulty_lower:
            continue
        searchable = " ".join([
            p.get("title", ""),
            p.get("task_id", ""),
            p.get("problem_description", ""),
            p.get("description", ""),
            " ".join(p.get("tags", [])),
            " ".join(p.get("topics", [])),
        ]).lower()
        if any(kw in searchable for kw in keywords):
            matched.append(p)

    return matched


def _build_reword_prompt(problem: dict) -> str:
    title       = problem.get("title", problem.get("task_id", ""))
    description = problem.get("problem_description", problem.get("description", ""))[:600]

    return f"""You are a technical problem designer.

Below is a coding problem. Your job is to REWORD the problem statement and title ONLY.

STRICT RULES:
- Keep the EXACT same algorithmic logic and solution approach.
- Keep the EXACT same input/output format.
- Change ONLY the real-world story/context (names, domain, scenario wording).
- The reworded version must be clearly different from the original wording.
- Do NOT simplify or make the problem easier or harder.
- Return ONLY valid JSON — no markdown, no extra text.

ORIGINAL TITLE: {title}

ORIGINAL DESCRIPTION:
{description}

Return this exact JSON structure:
{{
  "title": "Reworded title here",
  "description": "Reworded full problem description here — same logic, different story/context"
}}

Generate now:"""


class DSAQuestionRequest(BaseModel):
    difficulty: str
    topic: str
    concepts: List[str] = []
    languages: List[str] = []
    org_id: Optional[str] = None


@app.post("/api/v1/generate-dsa-question")
async def generate_dsa_question(body: DSAQuestionRequest, http_request: Request):
    """
    FAISS RAG-powered DSA question generation.
    Uses semantic search to find relevant problems.
    Falls back to keyword matching if FAISS unavailable.
    Rewrites problem wording using Qwen.
    """
    um = bind_usage_meta_from_request(http_request)
    rid = str(uuid.uuid4())
    t0 = time.perf_counter()
    request = body
    problems = _load_dsa_enriched()

    # Build search query from topic + concepts
    query = f"{request.topic} {' '.join(request.concepts)} {request.difficulty}"

    # Try FAISS search first
    faiss_available = _load_faiss_index()

    if faiss_available:
        logger.info(f"Using FAISS search for: {query}")
        matched = _faiss_search(query, request.difficulty, top_k=20)
        search_method = "faiss"
    else:
        logger.info(f"Using keyword search for: {query}")
        matched = _keyword_filter(problems, request.difficulty, request.topic, request.concepts)
        search_method = "keyword"

    # Fallback: difficulty only
    if not matched:
        logger.warning(f"No match found — falling back to difficulty only filter")
        matched = [p for p in problems if p.get("difficulty", "").lower() == request.difficulty.lower()]
        search_method = "difficulty_only"

    if not matched:
        raise HTTPException(
            status_code=404,
            detail=f"No problems found for difficulty='{request.difficulty}'"
        )

    # Random pick from top matches
    selected = random.choice(matched)
    logger.info(
        f"Selected: '{selected.get('title', selected.get('task_id'))}' "
        f"({selected.get('difficulty')}) via {search_method}"
    )

    # Reword using Qwen
    prompt = _build_reword_prompt(selected)

    try:
        messages = [
            {"role": "system", "content": "You are a technical problem designer. Return only valid JSON."},
            {"role": "user",   "content": prompt}
        ]
        text = TOKENIZER.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs_tok = TOKENIZER(text, return_tensors="pt").to(MODEL.device)
        output = MODEL.generate(
            **inputs_tok,
            max_new_tokens=1500,
            temperature=0.75,
            do_sample=True,
            top_p=0.9,
            repetition_penalty=1.1,
            pad_token_id=TOKENIZER.eos_token_id
        )
        decoded = TOKENIZER.decode(output[0], skip_special_tokens=True)
        decoded = decoded.split("assistant")[-1].strip()
        reworded = extract_json(decoded)

    except Exception as e:
        logger.error(f"Qwen reword failed: {e} — returning original wording")
        reworded = {
            "title":       selected.get("title", selected.get("task_id", "")),
            "description": selected.get("problem_description", selected.get("description", ""))
        }

    # Filter starter_code to requested languages only
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
        "original_title":     selected.get("title", selected.get("task_id", "")),
        "title":              reworded.get("title", selected.get("title", "")),
        "description":        reworded.get("description", selected.get("problem_description", "")),
        "function_signature": selected.get("function_signature", {}),
        "public_testcases":   selected.get("public_testcases", []),
        "hidden_testcases":   selected.get("hidden_testcases", []),
        "starter_code":       filtered_starter_code,
        "difficulty":         selected.get("difficulty", request.difficulty),
        "tags":               selected.get("tags", selected.get("topics", [])),
        "examples":           selected.get("examples", []),
        "example_images":     selected.get("example_images", []),
        "search_method":      search_method,
        "ai_generated":       True,
        "reworded":           True
    }


# ============================================================================
# AIML LIBRARY DATASET ENDPOINT v1.0
# Uses real datasets from sklearn/seaborn/statsmodels/keras/nltk/huggingface.
# Catalog: aiml_dataset_catalog.json (33 datasets, all direct load)
# Flow:
#   1. Match topic + concepts against catalog tags/domain
#   2. Pick best matching dataset
#   3. Qwen generates question around that real dataset
#   4. Return load_code baked into starter_code["python3"]
#   5. No data stored in DB — student loads directly in notebook
# ============================================================================

# ── AIML catalog paths (from settings.assets_dir) ────────────────────────────
def _aiml_catalog_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().aiml_catalog_path)


def _aiml_faiss_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().aiml_faiss_path)


def _aiml_metadata_path() -> str:
    from backend_app.core.settings import get_settings

    return str(get_settings().aiml_metadata_path)

_aiml_catalog_cache  = None
_aiml_faiss_index    = None
_aiml_meta_cache     = None
_aiml_embed_model    = None


def _load_aiml_catalog() -> list:
    global _aiml_catalog_cache
    if _aiml_catalog_cache is None:
        p = _aiml_catalog_path()
        if not os.path.exists(p):
            logger.warning(f"AIML catalog not found at {p}")
            return []
        with open(p, encoding="utf-8") as f:
            _aiml_catalog_cache = json.load(f)
        logger.info(f"Loaded {len(_aiml_catalog_cache)} datasets from AIML catalog")
    return _aiml_catalog_cache


def _load_aiml_faiss() -> bool:
    """
    Loads AIML FAISS index + metadata + embedding model.
    Returns True if successful, False if index not available.
    Falls back to keyword matching when False.
    """
    global _aiml_faiss_index, _aiml_meta_cache, _aiml_embed_model
    if _aiml_faiss_index is not None:
        return True
    if not os.path.exists(_aiml_faiss_path()):
        logger.warning("AIML FAISS index not found — falling back to keyword matching")
        return False
    try:
        import faiss as _faiss
        from sentence_transformers import SentenceTransformer as _ST
        logger.info("Loading AIML FAISS index...")
        _aiml_faiss_index = _faiss.read_index(_aiml_faiss_path())
        with open(_aiml_metadata_path(), encoding="utf-8") as f:
            _aiml_meta_cache = json.load(f)
        # Reuse DSA embed model if already loaded — same model
        if _dsa_embed_model is not None:
            _aiml_embed_model = _dsa_embed_model
        else:
            logger.info("Loading AIML embedding model...")
            _aiml_embed_model = _ST("all-MiniLM-L6-v2")
        logger.info(f"AIML FAISS ready: {_aiml_faiss_index.ntotal} vectors")
        return True
    except Exception as e:
        logger.warning(f"AIML FAISS load failed: {e} — falling back to keyword matching")
        return False



# ============================================================================
# AIML DATASET REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
# Maps topic-signal keywords → required catalog tags.
# When a topic matches an entry here, the returned dataset MUST contain ALL
# of the listed required_tags in its own tags list.  If no catalog entry
# satisfies both the semantic/keyword score AND these required tags, the
# system falls back to synthetic generation rather than returning a wrong
# dataset.
#
# This is the single source of truth that prevents FAISS from drifting:
#   "flower classification" → beans (plant), NOT fashion-mnist (retail)
#   "iris"                 → sklearn-iris, NOT penguins
#   "customer churn"       → churn dataset, NOT generic binary classification
#
# RULES FOR EDITING:
#   - topic_signals: lowercase substrings that trigger this entry
#   - required_tags: ALL must appear in the matched dataset's tags
#   - preferred_ids: catalog IDs checked first before any search (exact match)
#   - forbidden_ids: catalog IDs that must NEVER be returned for this topic
# ============================================================================

_AIML_DATASET_REGISTRY: list = [
    # ── Classification — specific named datasets ──────────────────────────
    {
        "topic_signals": ["iris", "iris flower", "iris classification"],
        "required_tags": ["flowers"],
        "preferred_ids": ["sklearn-iris"],
        "forbidden_ids": ["seaborn-penguins", "hf-beans"],
    },
    {
        "topic_signals": ["penguin", "palmer penguin"],
        "required_tags": ["biology"],
        "preferred_ids": ["seaborn-penguins"],
        "forbidden_ids": ["sklearn-iris"],
    },
    {
        "topic_signals": ["titanic", "titanic survival", "passenger survival"],
        "required_tags": ["titanic"],
        "preferred_ids": ["seaborn-titanic", "openml-titanic", "openml-titanic-survival"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["mnist", "handwritten digit", "digit recognition", "handwriting recognition"],
        "required_tags": ["digits"],
        "preferred_ids": ["keras-mnist", "openml-mnist-784", "sklearn-digits"],
        "forbidden_ids": ["keras-fashion-mnist"],
    },
    {
        "topic_signals": ["fashion mnist", "clothing classification", "apparel classification", "fashion product"],
        "required_tags": ["fashion"],
        "preferred_ids": ["keras-fashion-mnist"],
        "forbidden_ids": ["keras-mnist"],
    },
    {
        "topic_signals": ["cifar", "cifar-10", "cifar10", "object recognition", "object classification"],
        "required_tags": ["object-recognition"],
        "preferred_ids": ["keras-cifar10", "hf-cifar10-hf"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["flower classification", "flower recognition", "flower detection"],
        "required_tags": ["agriculture"],
        "preferred_ids": ["hf-beans", "hf-oxford-pets"],
        "forbidden_ids": ["sklearn-iris", "keras-fashion-mnist", "keras-mnist"],
    },
    # ── Churn / Retention ─────────────────────────────────────────────────
    {
        "topic_signals": ["customer churn", "churn prediction", "churn analysis",
                          "churn detection", "user churn", "subscriber churn",
                          "retention prediction", "customer retention"],
        "required_tags": ["churn"],
        "preferred_ids": ["openml-telco-churn", "openml-bank-churn"],
        "forbidden_ids": ["sklearn-make-classification", "sklearn-make-blobs",
                          "sklearn-make-moons", "sklearn-make-circles"],
    },
    # ── HR / Attrition ────────────────────────────────────────────────────
    {
        "topic_signals": ["employee attrition", "hr attrition", "staff turnover",
                          "employee churn", "workforce attrition", "talent retention"],
        "required_tags": ["attrition"],
        "preferred_ids": ["openml-hr-attrition"],
        "forbidden_ids": ["openml-telco-churn"],
    },
    # ── Fraud / Anomaly ───────────────────────────────────────────────────
    {
        "topic_signals": ["fraud detection", "credit card fraud", "transaction fraud",
                          "payment fraud", "financial fraud"],
        "required_tags": ["fraud"],
        "preferred_ids": ["openml-fraud-detection"],
        "forbidden_ids": ["sklearn-make-classification"],
    },
    # ── Healthcare ────────────────────────────────────────────────────────
    {
        "topic_signals": ["diabetes prediction", "diabetes detection", "diabetes classification",
                          "blood sugar prediction", "glucose prediction"],
        "required_tags": ["diabetes"],
        "preferred_ids": ["openml-pima-diabetes", "sklearn-diabetes"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["heart disease", "cardiac prediction", "heart attack prediction",
                          "cardiovascular", "heart failure"],
        "required_tags": ["heart-disease"],
        "preferred_ids": ["openml-heart-disease", "statsmodels-heart"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["breast cancer", "cancer detection", "tumor classification",
                          "malignant benign", "cancer prediction"],
        "required_tags": ["cancer"],
        "preferred_ids": ["sklearn-breast-cancer"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["stroke prediction", "stroke detection", "stroke risk"],
        "required_tags": ["stroke"],
        "preferred_ids": ["openml-stroke-prediction"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["covid", "covid-19", "coronavirus", "pandemic prediction"],
        "required_tags": ["covid-19"],
        "preferred_ids": ["openml-covid-symptoms"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["obesity", "bmi prediction", "weight classification"],
        "required_tags": ["obesity"],
        "preferred_ids": ["openml-obesity-levels"],
        "forbidden_ids": [],
    },
    # ── Finance / Credit ──────────────────────────────────────────────────
    {
        "topic_signals": ["credit risk", "loan default", "credit default",
                          "credit scoring", "default prediction"],
        "required_tags": ["credit"],
        "preferred_ids": ["openml-default-credit", "openml-credit-g",
                          "openml-loan-approval", "openml-givemecredit"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["stock price", "stock prediction", "stock market",
                          "financial forecasting", "equity prediction"],
        "required_tags": ["stock"],
        "preferred_ids": ["openml-stock-sp500", "openml-bitcoin-price"],
        "forbidden_ids": [],
    },
    # ── NLP ───────────────────────────────────────────────────────────────
    {
        "topic_signals": ["sentiment analysis", "opinion mining", "review sentiment",
                          "text sentiment", "positive negative classification"],
        "required_tags": ["sentiment"],
        "preferred_ids": ["hf-imdb", "hf-sst2", "hf-yelp-review",
                          "nltk-movie-reviews", "keras-imdb"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["spam detection", "email spam", "sms spam", "spam classification"],
        "required_tags": ["spam"],
        "preferred_ids": ["hf-spam-detection"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["fake news", "misinformation detection", "news credibility"],
        "required_tags": ["fake-news"],
        "preferred_ids": ["hf-fake-news"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["named entity recognition", "ner", "entity extraction",
                          "information extraction"],
        "required_tags": ["ner"],
        "preferred_ids": ["hf-conll2003"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["text summarization", "document summarization", "abstractive summarization",
                          "extractive summarization", "news summarization"],
        "required_tags": ["summarization"],
        "preferred_ids": ["hf-pubmed-summarization", "hf-abstractive-summarization"],
        "forbidden_ids": [],
    },
    # ── CV / Image ────────────────────────────────────────────────────────
    {
        "topic_signals": ["medical image", "chest x-ray", "xray classification",
                          "pneumonia detection", "radiology"],
        "required_tags": ["medical-imaging"],
        "preferred_ids": ["hf-chest-xray", "hf-pneumonia-xray", "hf-brain-tumor-mri"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["plant disease", "crop disease", "leaf disease",
                          "plant classification", "agriculture classification"],
        "required_tags": ["agriculture"],
        "preferred_ids": ["hf-beans", "hf-plant-village"],
        "forbidden_ids": ["sklearn-iris"],
    },
    {
        "topic_signals": ["face emotion", "facial emotion", "emotion recognition",
                          "facial expression", "affect recognition"],
        "required_tags": ["emotion"],
        "preferred_ids": ["hf-emotion-face"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["traffic sign", "road sign detection", "sign recognition",
                          "autonomous driving"],
        "required_tags": ["traffic-signs"],
        "preferred_ids": ["hf-traffic-signs"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["satellite image", "remote sensing", "aerial image",
                          "land cover", "land use classification"],
        "required_tags": ["satellite"],
        "preferred_ids": ["hf-eurosat", "hf-satellite-land-use"],
        "forbidden_ids": [],
    },
    # ── Time Series ───────────────────────────────────────────────────────
    {
        "topic_signals": ["energy forecasting", "electricity forecasting",
                          "power consumption", "energy prediction"],
        "required_tags": ["energy"],
        "preferred_ids": ["openml-electricity", "hf-ett-time-series",
                          "openml-power-consumption"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["weather forecasting", "temperature prediction",
                          "climate forecasting", "meteorological prediction"],
        "required_tags": ["weather"],
        "preferred_ids": ["hf-weather-jena"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["predictive maintenance", "equipment failure",
                          "rul prediction", "remaining useful life", "iot anomaly"],
        "required_tags": ["predictive-maintenance"],
        "preferred_ids": ["openml-iot-predictive-maintenance"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["air quality", "pollution prediction", "pm2.5", "aqi prediction"],
        "required_tags": ["air-quality"],
        "preferred_ids": ["openml-air-quality", "openml-pm25-beijing"],
        "forbidden_ids": [],
    },
    # ── Recommendation / Clustering ───────────────────────────────────────
    {
        "topic_signals": ["recommendation", "movie recommendation", "collaborative filtering",
                          "rating prediction", "recommender system"],
        "required_tags": ["recommendation"],
        "preferred_ids": ["openml-movielens-100k"],
        "forbidden_ids": [],
    },
    {
        "topic_signals": ["customer segmentation", "market segmentation",
                          "user clustering", "k-means clustering"],
        "required_tags": ["segmentation"],
        "preferred_ids": ["openml-mall-customers"],
        "forbidden_ids": [],
    },
    # ── Network / Security ────────────────────────────────────────────────
    {
        "topic_signals": ["network intrusion", "intrusion detection", "cybersecurity",
                          "dos attack", "network attack detection"],
        "required_tags": ["network-intrusion"],
        "preferred_ids": ["openml-nsl-kdd"],
        "forbidden_ids": [],
    },
    # ── Housing / Real Estate ─────────────────────────────────────────────
    {
        "topic_signals": ["house price", "housing price", "real estate prediction",
                          "property price", "home price"],
        "required_tags": ["real-estate"],
        "preferred_ids": ["sklearn-california-housing"],
        "forbidden_ids": [],
    },
    # ── Supply Chain / Logistics ──────────────────────────────────────────
    {
        "topic_signals": ["supply chain", "delivery prediction", "logistics",
                          "shipping delay", "on-time delivery"],
        "required_tags": ["supply-chain"],
        "preferred_ids": ["openml-ecommerce-shipping"],
        "forbidden_ids": [],
    },
]

# ── Concept → expected tag mapping ───────────────────────────────────────────
# If a concept keyword is present in the request, the matched dataset's tags
# should contain at least one of the allowed_tags.  This prevents concept drift:
# e.g. concept="time series forecasting" should not match a tabular classifier.
_CONCEPT_TAG_MAP: dict = {
    "time series":        ["time-series", "forecasting", "arima", "lstm", "temporal"],
    "forecasting":        ["time-series", "forecasting", "regression"],
    "nlp":                ["nlp", "text", "sentiment", "bert", "language"],
    "text classification": ["nlp", "text", "classification"],
    "image classification": ["cv", "image", "cnn", "vision"],
    "computer vision":    ["cv", "image", "cnn", "vision"],
    "deep learning":      ["deep-learning", "cnn", "lstm", "transformer", "bert"],
    "transfer learning":  ["transfer-learning", "cnn", "resnet"],
    "clustering":         ["clustering", "unsupervised", "segmentation", "kmeans"],
    "anomaly detection":  ["anomaly-detection", "fraud", "intrusion", "outlier"],
    "recommendation":     ["recommendation", "collaborative-filtering", "ratings"],
    "graph":              ["graph", "gnn", "node-classification"],
    "regression":         ["regression", "continuous"],
    "classification":     ["classification", "binary", "multiclass"],
    "imbalanced":         ["imbalanced"],
    "fraud":              ["fraud", "anomaly-detection"],
    "churn":              ["churn"],
    "sentiment":          ["sentiment", "nlp"],
    "speech":             ["speech", "audio", "asr"],
    "audio":              ["audio", "speech", "mfcc"],
}


def _registry_lookup(topic: str, concepts: list, catalog: list) -> dict | None:
    """
    Check the registry for an exact topic signal match.
    Returns the best preferred_id dataset from the catalog if found,
    or the first catalog entry that satisfies required_tags.
    Returns None if topic does not match any registry entry.
    """
    topic_lower = topic.lower()
    all_text    = topic_lower + " " + " ".join(c.lower() for c in concepts)

    for entry in _AIML_DATASET_REGISTRY:
        # Check if any signal matches
        matched_signal = any(sig in all_text for sig in entry["topic_signals"])
        if not matched_signal:
            continue

        required_tags = set(entry.get("required_tags", []))
        forbidden_ids = set(entry.get("forbidden_ids", []))
        preferred_ids = entry.get("preferred_ids", [])

        # Try preferred IDs first — exact catalog lookup
        for pid in preferred_ids:
            for ds in catalog:
                if ds["id"] == pid and pid not in forbidden_ids:
                    logger.info(f"Registry exact match: '{ds['name']}' for topic='{topic}'")
                    return ds

        # Fall back to required_tags scan within catalog
        for ds in catalog:
            if ds["id"] in forbidden_ids:
                continue
            ds_tags = set(t.lower() for t in ds.get("tags", []))
            if required_tags and required_tags.issubset(ds_tags):
                logger.info(
                    f"Registry tag match: '{ds['name']}' "
                    f"(required_tags={required_tags}) for topic='{topic}'"
                )
                return ds

        # Signal matched but no valid dataset found — stop here, do NOT fall through
        # to FAISS which would return the wrong dataset
        logger.warning(
            f"Registry signal matched '{topic}' but no valid catalog entry "
            f"satisfies required_tags={required_tags} — will use synthetic"
        )
        return None  # Explicit: synthetic is better than wrong dataset

    return None  # No registry entry matched — proceed to FAISS/keyword


def _concept_tags_satisfied(dataset: dict, concepts: list) -> bool:
    """
    Check that the matched dataset's tags are compatible with the requested concepts.
    Prevents concept drift — e.g. concept='time series' matched to a tabular classifier.
    Returns True if no concept conflict is detected.
    """
    if not concepts:
        return True

    ds_tags = set(t.lower() for t in dataset.get("tags", []))
    ds_category = dataset.get("category", "").lower()
    ds_tags.add(ds_category)  # category counts as a tag for this check

    for concept in concepts:
        concept_lower = concept.lower()
        for key, allowed_tags in _CONCEPT_TAG_MAP.items():
            if key in concept_lower:
                # At least one allowed tag must appear in dataset tags
                if not any(at in ds_tags for at in allowed_tags):
                    logger.warning(
                        f"Concept conflict: concept='{concept}' requires one of "
                        f"{allowed_tags} but dataset '{dataset['name']}' has tags={ds_tags}"
                    )
                    return False
    return True


def _difficulty_compatible(dataset: dict, difficulty: str) -> bool:
    """
    Check difficulty compatibility.
    IMPORTANT: same dataset is used across difficulties — only task complexity changes.
    This function checks if a dataset is broadly appropriate for the difficulty level,
    NOT that it must be an exact match.  A 'Hard' dataset can also be used for Easy
    (task complexity is scaled by _build_task_scaffold, not by swapping datasets).
    """
    ds_diffs = [d.lower() for d in dataset.get("difficulty", [])]
    if not ds_diffs:
        return True  # No difficulty restriction in catalog entry
    difficulty_lower = difficulty.lower()
    # Hard can always use Medium/Hard datasets; Easy can use Easy/Medium
    compat = {
        "easy":   {"easy", "medium"},
        "medium": {"easy", "medium", "hard"},
        "hard":   {"easy", "medium", "hard"},
    }
    allowed = compat.get(difficulty_lower, {"easy", "medium", "hard"})
    return bool(set(ds_diffs) & allowed)


def _match_dataset(topic: str, concepts: list, difficulty: str):
    """
    Production-grade dataset matching.

    Pipeline (in order, stop at first success):
      1. Registry lookup  — exact topic signal → required_tags check
      2. FAISS search     — semantic similarity, then _validate_match()
      3. Keyword fallback — tag/domain overlap, then _validate_match()
      4. None             — caller falls back to synthetic generation

    Key properties:
      - Registry always wins over FAISS for known topics
      - FAISS result is validated for concept compatibility before returning
      - Difficulty does NOT swap datasets — all difficulties can use the same dataset
      - Forbidden dataset list prevents known-wrong pairings
    """
    catalog = _load_aiml_catalog()
    if not catalog:
        return None

    difficulty_lower = difficulty.lower()

    # ── Step 1: Registry lookup ───────────────────────────────────────────────
    registry_result = _registry_lookup(topic, concepts, catalog)
    if registry_result is not None:
        # Registry returned a dataset — validate concept compatibility
        if _concept_tags_satisfied(registry_result, concepts):
            return registry_result
        else:
            logger.warning(
                f"Registry match '{registry_result['name']}' failed concept check "
                f"for concepts={concepts} — falling back to FAISS"
            )
            # Do NOT return it; continue to FAISS

    # ── Step 2: FAISS semantic search ─────────────────────────────────────────
    faiss_available = _load_aiml_faiss()

    if faiss_available:
        try:
            query = f"{topic} {' '.join(concepts)} machine learning dataset"
            query_vec = _aiml_embed_model.encode(
                [query],
                convert_to_numpy=True,
                normalize_embeddings=True
            ).astype(np.float32)

            # Search top 30 — validate each result before accepting
            scores, indices = _aiml_faiss_index.search(
                query_vec, min(30, _aiml_faiss_index.ntotal)
            )

            for idx, score in zip(indices[0], scores[0]):
                if idx < 0 or idx >= len(_aiml_meta_cache):
                    continue
                meta         = _aiml_meta_cache[idx]
                catalog_idx  = meta.get("index", idx)
                if catalog_idx >= len(catalog):
                    continue

                dataset = catalog[catalog_idx]

                # Guard 1: difficulty compatibility
                if not _difficulty_compatible(dataset, difficulty_lower):
                    continue

                # Guard 2: concept compatibility — reject drift
                if not _concept_tags_satisfied(dataset, concepts):
                    logger.info(
                        f"FAISS: skipping '{dataset['name']}' — concept mismatch "
                        f"(score={score:.3f})"
                    )
                    continue

                # Guard 3: minimum FAISS confidence threshold
                # Below 0.25 the match is too weak — better to go synthetic
                if score < 0.25:
                    logger.info(
                        f"FAISS: score {score:.3f} too low for '{dataset['name']}' "
                        f"— stopping FAISS scan"
                    )
                    break

                logger.info(
                    f"AIML FAISS match: '{dataset['name']}' "
                    f"(score={score:.3f}, difficulty={difficulty})"
                )
                return dataset

            logger.info("AIML FAISS: no valid match after guards — trying keyword fallback")
        except Exception as e:
            logger.warning(f"AIML FAISS search failed: {e} — falling back to keyword")

    # ── Step 3: Keyword fallback ──────────────────────────────────────────────
    topic_words   = set(topic.lower().split())
    concept_words = set(" ".join(concepts).lower().split())
    best_match    = None
    best_score    = 0

    for dataset in catalog:
        score    = 0
        tags     = [t.lower() for t in dataset.get("tags", [])]
        domain   = dataset.get("domain", "").lower()
        ds_diffs = [d.lower() for d in dataset.get("difficulty", [])]

        for tag in tags:
            for word in topic_words:
                if word in tag or tag in word:
                    score += 3
                    break

        for tag in tags:
            for word in concept_words:
                if word in tag or tag in word:
                    score += 2
                    break

        for word in topic_words | concept_words:
            if word in domain:
                score += 1

        if difficulty_lower in ds_diffs:
            score += 1

        if score > best_score:
            best_score = score
            best_match = dataset

    # Minimum score AND concept check before accepting keyword match
    if best_score >= 4 and best_match and _concept_tags_satisfied(best_match, concepts):
        logger.info(f"AIML keyword match: '{best_match['name']}' (score={best_score})")
        return best_match

    logger.info(
        f"No valid dataset match (keyword score={best_score}, "
        f"topic='{topic}') — using synthetic generation"
    )
    return None


def _build_aiml_library_prompt(request_data: dict, dataset: dict) -> str:
    topic       = request_data.get("topic", "")
    difficulty  = request_data.get("difficulty", "Medium")
    concepts    = request_data.get("concepts", [])
    concepts_str = ", ".join(concepts) if concepts else "general ML"

    return f"""You are an expert AI/ML assessment designer.

Generate a {difficulty} difficulty AI/ML problem using this REAL dataset.

DATASET INFORMATION:
Name: {dataset.get('name', '')}
Source: {dataset.get('source', '')}
Domain: {dataset.get('domain', '')}
Description: {dataset.get('description', '')}
Features: {dataset.get('features_info', '')}
Target: {dataset.get('target', '')}
Target type: {dataset.get('target_type', '')}
Size: {dataset.get('size', '')}

ASSESSMENT TOPIC: {topic}
CONCEPTS TO TEST: {concepts_str}
DIFFICULTY: {difficulty}

RULES:
- Write a realistic real-world problem statement around THIS specific dataset.
- Tasks must reference the ACTUAL feature names from this dataset.
- Do NOT suggest loading a different dataset.
- Do NOT generate synthetic data.
- expectedApproach must suggest algorithms appropriate for this dataset target type.
- evaluationCriteria must match the target type (classification vs regression metrics).
- ALL fields are REQUIRED.

Return ONLY this JSON:
{{
  "problemStatement": "Detailed real-world problem description grounded in the actual dataset domain",
  "tasks": [
    "Task 1: Data Loading and Exploration — load the {dataset.get('name', '')} dataset using the provided load_code. Examine the actual columns specific to this dataset. Display shape, first 10 rows, check missing values per column, data types, and summary statistics relevant to {topic}.",
    "Task 2: Data Preprocessing — handle any missing values in this specific dataset. Identify which features from {dataset.get('name', '')} need encoding or normalization. Apply appropriate transformations. Split 80/20 train/test.",
    "Task 3: Exploratory Data Analysis — visualize the {dataset.get('target', 'target')} distribution. Plot correlations between features in this {dataset.get('domain', 'domain')} dataset. Create 2-3 meaningful domain-specific plots for {topic}.",
    "Task 4: Model Training — train at least 2 ML models best suited for this {dataset.get('target_type', '')} problem using {dataset.get('name', '')} features. Evaluate with metrics appropriate for this target type.",
    "Task 5: Model Comparison and {dataset.get('domain', 'Domain')} Insights — compare model performance on this specific dataset. Identify the most predictive features. Provide actionable {dataset.get('domain', 'domain')}-specific recommendations for {topic}."
  ],
  "preprocessing_requirements": [
    "Specific step 1 for THIS dataset",
    "Specific step 2 for THIS dataset",
    "Specific step 3 for THIS dataset"
  ],
  "expectedApproach": "2-3 specific ML algorithms suited for this exact dataset with reasoning.",
  "evaluationCriteria": ["metric1", "metric2", "metric3"],
  "difficulty": "{difficulty}",
  "bloomLevel": "Apply"
}}

Generate now:"""


class AIMLLibraryRequest(BaseModel):
    topic: str
    difficulty: str
    concepts: List[str] = []
    use_cache: bool = True
    org_id: Optional[str] = None


@app.get("/api/v1/aiml-library/catalog/{catalog_id}/preview")
async def aiml_library_catalog_preview(catalog_id: str):
    """
    Return a small tabular preview for a catalog ``id`` when ``load_code`` uses OpenML
    (same logic as inline preview on generate-aiml-library). Does not call the LLM.
    """
    from backend_app.engine.aiml_library_preview import preview_catalog_by_id

    rows, err = preview_catalog_by_id(catalog_id)
    if err == "not_found":
        raise HTTPException(status_code=404, detail=f"Unknown catalog_id: {catalog_id}")
    if rows is not None:
        return {
            "catalog_id": catalog_id,
            "preview_available": True,
            "data_preview": True,
            "rows": rows,
            "row_count": len(rows),
        }
    return {
        "catalog_id": catalog_id,
        "preview_available": False,
        "data_preview": False,
        "rows": [],
        "reason": err or "unavailable",
    }


@app.post("/api/v1/generate-aiml-library")
async def generate_aiml_library(body: AIMLLibraryRequest, http_request: Request):
    """
    AIML question generation using real library datasets.
    Matches topic/concepts to best dataset in aiml_dataset_catalog.json.
    Returns load_code baked into starter_code for student Jupyter notebook.
    Falls back to synthetic generation if no dataset match found.
    """
    update_stats("aiml")
    um = bind_usage_meta_from_request(http_request)
    data = body.model_dump()

    job_id = str(uuid.uuid4())
    JOB_STORE[job_id] = {"status": "pending", "result": None, "error": None}

    async def _task():
        t_outer = time.time()
        JOB_STORE[job_id]["status"] = "processing"
        try:
            item_data = {k: v for k, v in data.items()}
            cache_key = generate_cache_key("aiml_library", item_data)

            if body.use_cache:
                cached = get_from_cache(cache_key)
                if cached:
                    cached["cache_hit"] = True
                    JOB_STORE[job_id] = {
                        "status": "complete",
                        "result": {"aiml_problems": [cached], "generation_time_seconds": 0, "cache_hit": True, "batched": False, "batch_size": 1},
                        "error": None,
                    }
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=True,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )
                    return

            matched = _match_dataset(body.topic, body.concepts, body.difficulty)

            if matched:
                logger.info(f"Using library dataset: {matched['name']}")
                prompt = _build_aiml_library_prompt(item_data, matched)

                try:
                    messages = [
                        {"role": "system", "content": "You are an expert AI/ML assessment designer. Return only valid JSON."},
                        {"role": "user",   "content": prompt}
                    ]
                    text = TOKENIZER.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
                    inputs_tok = TOKENIZER(text, return_tensors="pt").to(MODEL.device)
                    gen_t0 = time.time()
                    output = MODEL.generate(
                        **inputs_tok,
                        max_new_tokens=2000,
                        temperature=0.6,
                        do_sample=True,
                        top_p=0.9,
                        repetition_penalty=1.1,
                        pad_token_id=TOKENIZER.eos_token_id
                    )
                    try:
                        _in_tok = int(inputs_tok["attention_mask"].sum(dim=-1).max().item())
                        _out_tok = int(output.shape[1] - _in_tok)
                        from backend_app.billing.metering import current_token_counts

                        current_token_counts.set(
                            {
                                "prompt_tokens": _in_tok,
                                "completion_tokens": max(0, _out_tok),
                                "total_tokens": max(0, _in_tok + _out_tok),
                            }
                        )
                    except Exception:
                        pass
                    gen_time = time.time() - gen_t0
                    decoded  = TOKENIZER.decode(output[0], skip_special_tokens=True)
                    decoded  = decoded.split("assistant")[-1].strip()
                    result   = extract_json(decoded)

                    load_code = matched.get("load_code", "")
                    starter   = (
                        f"# Dataset: {matched['name']} ({matched['source']})\n"
                        f"# Run this cell to load your data\n\n"
                        f"{load_code}\n\n"
                        f"# Your solution below\n"
                    )

                    problem = {
                        "problemStatement":           result.get("problemStatement", ""),
                        "tasks":                      result.get("tasks", []),
                        "preprocessing_requirements": result.get("preprocessing_requirements", []),
                        "expectedApproach":           result.get("expectedApproach", ""),
                        "evaluationCriteria":         result.get("evaluationCriteria", []),
                        "difficulty":                 result.get("difficulty", body.difficulty),
                        "bloomLevel":                 result.get("bloomLevel", "Apply"),
                        "dataset": {
                            "catalog_id":  matched.get("id", ""),
                            "name":        matched.get("name", ""),
                            "source":      matched.get("source", ""),
                            "description": matched.get("description", ""),
                            "domain":      matched.get("domain", ""),
                            "size":        matched.get("size", ""),
                            "target":      matched.get("target", ""),
                            "target_type": matched.get("target_type", ""),
                            "load_code":   load_code,
                            "import_code": matched.get("import_code", ""),
                            "pip_install": matched.get("pip_install", ""),
                            "features_info": matched.get("features_info", ""),
                            "tags":        matched.get("tags", []),
                            "use_case":    matched.get("use_case", ""),
                            "category":    matched.get("category", ""),
                            "direct_load": True,
                            "storage_type": "library",
                            "file_id":     None,
                        },
                        "starter_code":      {"python3": starter},
                        "dataset_load_code": load_code,
                        "dataset_strategy":  "library",
                        "generation_time_seconds": round(gen_time, 3),
                        "cache_hit": False,
                    }

                    try:
                        from backend_app.engine.aiml_library_preview import try_library_preview_rows

                        _prev_rows = try_library_preview_rows(matched)
                        if _prev_rows:
                            problem["dataset"]["data"] = _prev_rows
                            problem["dataset"]["data_preview"] = True
                    except Exception as _prev_err:
                        logger.debug("AIML library data preview skipped: %s", _prev_err)

                    # ── Semantic validation of library output ──────────────
                    _is_valid, _issues = validate_aiml_output(
                        problem,
                        item_data.get("topic", ""),
                        item_data.get("concepts", []),
                        item_data.get("difficulty", "Medium"),
                        matched_dataset=matched,
                    )
                    if not _is_valid:
                        logger.warning(
                            f"Library AIML output has quality issues — returning with warnings: {_issues}"
                        )
                        problem["validation_warnings"] = _issues
                    # ──────────────────────────────────────────────────────

                    save_to_cache(cache_key, problem)
                    JOB_STORE[job_id] = {
                        "status": "complete",
                        "result": {"aiml_problems": [problem], "generation_time_seconds": round(gen_time, 3), "cache_hit": False, "batched": False, "batch_size": 1},
                        "error": None,
                    }
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=False,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )

                except Exception as e:
                    logger.error(f"Library generation failed: {e} — falling back to synthetic")
                    token_limit = calculate_aiml_token_limit(item_data)
                    result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)
                    result["dataset_strategy"] = "synthetic_fallback"
                    # Validate synthetic fallback too
                    _is_valid, _issues = validate_aiml_output(
                        result,
                        item_data.get("topic", ""),
                        item_data.get("concepts", []),
                        item_data.get("difficulty", "Medium"),
                        matched_dataset=None,
                    )
                    if not _is_valid:
                        result["validation_warnings"] = _issues
                    save_to_cache(cache_key, result)
                    JOB_STORE[job_id] = {
                        "status": "complete",
                        "result": {"aiml_problems": [result], "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3), "cache_hit": False, "batched": False, "batch_size": 1},
                        "error": None,
                    }
                    _emit_usage_metering(
                        job_id=job_id,
                        usage_meta=um,
                        route="generate-aiml-library",
                        cache_hit=False,
                        latency_ms=(time.time() - t_outer) * 1000,
                        status="success",
                    )
            else:
                logger.info("No catalog match — using synthetic generation")
                token_limit = calculate_aiml_token_limit(item_data)
                result = await add_to_batch_and_wait("aiml", item_data, cache_key, build_aiml_prompt, token_limit)
                result["dataset_strategy"] = "synthetic"
                # Validate no-match synthetic output
                _is_valid, _issues = validate_aiml_output(
                    result,
                    item_data.get("topic", ""),
                    item_data.get("concepts", []),
                    item_data.get("difficulty", "Medium"),
                    matched_dataset=None,
                )
                if not _is_valid:
                    result["validation_warnings"] = _issues
                save_to_cache(cache_key, result)
                JOB_STORE[job_id] = {
                    "status": "complete",
                    "result": {"aiml_problems": [result], "generation_time_seconds": round(result.get("generation_time_seconds", 0), 3), "cache_hit": False, "batched": False, "batch_size": 1},
                    "error": None,
                }
                _emit_usage_metering(
                    job_id=job_id,
                    usage_meta=um,
                    route="generate-aiml-library",
                    cache_hit=False,
                    latency_ms=(time.time() - t_outer) * 1000,
                    status="success",
                )

        except Exception as e:
            STATS["errors"] += 1
            JOB_STORE[job_id] = {"status": "failed", "result": None, "error": str(e)}
            _emit_usage_metering(
                job_id=job_id,
                usage_meta=um,
                route="generate-aiml-library",
                cache_hit=False,
                latency_ms=(time.time() - t_outer) * 1000,
                status="error",
                error_detail=str(e)[:500],
            )

    asyncio.create_task(_task())
    return {"job_id": job_id, "status": "pending"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9000)
# v1.0.2
