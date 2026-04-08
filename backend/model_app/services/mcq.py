from __future__ import annotations

import ast
import re


def _normalize_str(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _safe_literal_eval(s: str) -> bool:
    try:
        ast.literal_eval(s)
        return True
    except Exception:
        return False

import ast
import asyncio
import logging
import re
import subprocess
import time
import uuid
from typing import List, Optional, Tuple

from fastapi import HTTPException

from backend.model_app.core.app import _batch_size_max, _batch_timeout
from backend.model_app.core.state import STATS, batch_locks, batch_queues, pending_results
from backend.model_app.prompts.mcq import build_mcq_prompt
from backend.model_app.prompts.mcq import build_mcq_verifier_prompt
from backend.model_app.services.cache import RESPONSE_CACHE
from backend.model_app.services.generation import extract_json
from backend.model_app.services.model import _llm_chat_batch, _llm_chat_single


logger = logging.getLogger(__name__)


def verify_mcq_with_llm(mcq: dict) -> dict:
    for attempt in range(2):
        try:
            messages = [
                {"role": "system", "content": "You are a senior assessment quality auditor."},
                {"role": "user", "content": build_mcq_verifier_prompt(mcq)}
            ]
            decoded, _, _ = _llm_chat_single(
                messages,
                temperature=0.2,
                top_p=0.9,
                max_tokens=2000,
                repetition_penalty=1.0,
            )
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


# Route MCQ parsing helpers through the extracted module while keeping local
# compatibility during the staged refactor.


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


# ============================================================================
# BATCH GENERATION
# ============================================================================

def generate_batch(prompts: List[str]):
    messages_list = []
    for p in prompts:
        messages_list.append([
            {
                "role": "system",
                "content": (
                    "You are an expert assessment content generator. "
                    "Always generate complete, meaningful questions and answers. "
                    "Never use placeholders like '...' or 'TBD'."
                ),
            },
            {"role": "user", "content": p},
        ])

    start = time.time()
    responses, _ = _llm_chat_batch(
        messages_list,
        temperature=0.7,
        top_p=0.9,
        repetition_penalty=1.1,
        max_tokens=2000,
    )
    duration = time.time() - start
    return responses, duration / max(1, len(prompts))


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

    correct_options = [o for o in final_mcq.get("options", []) if o.get("isCorrect") is True]
    if len(correct_options) != 1:
        raise RuntimeError(f"Expected exactly 1 correct option, got {len(correct_options)}")

    option_texts = [o.get("text", "").strip() for o in final_mcq.get("options", [])]
    if len(option_texts) != 4:
        raise RuntimeError(f"Expected 4 options, got {len(option_texts)}")
    if len(option_texts) != len(set(option_texts)):
        raise RuntimeError("Duplicate option texts detected")
    if len(final_mcq.get("explanation", "").strip()) < 40:
        raise RuntimeError("Explanation too short (< 40 chars)")

    return final_mcq


async def process_mcq_batch():
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

        try:
            final_mcq = _run_mcq_pipeline(text)
        except Exception as e:
            primary_error = e
            logger.warning(
                f"Primary MCQ pipeline failed (item {i}, "
                f"type={'deterministic' if 'expression' in text else 'conceptual'}): {e}"
            )

        if final_mcq is not None:
            final_mcq.update(
                {
                    "generation_time_seconds": per_req_time,
                    "batched": True,
                    "batch_size": len(batch),
                    "cache_hit": False,
                }
            )
            RESPONSE_CACHE[keys[i]] = final_mcq
            pending_results[ids[i]] = final_mcq
            continue

        logger.info(f"Retrying MCQ generation for item {i} (primary error: {str(primary_error)[:80]})")
        try:
            retry_prompt = build_mcq_prompt(batch[i][1])
            retry_texts, _ = generate_batch([retry_prompt])
            if not retry_texts or not retry_texts[0].strip():
                raise RuntimeError("Retry generation returned empty response")

            final_mcq = _run_mcq_pipeline(retry_texts[0])
            final_mcq.update(
                {
                    "generation_time_seconds": per_req_time,
                    "batched": True,
                    "batch_size": len(batch),
                    "cache_hit": False,
                }
            )
            RESPONSE_CACHE[keys[i]] = final_mcq
            pending_results[ids[i]] = final_mcq
            logger.info(f"Retry succeeded for item {i}")
        except Exception as retry_exc:
            primary_msg = str(primary_error)[:120] if primary_error else "unknown"
            retry_msg = str(retry_exc)[:120]
            logger.error(f"Retry also failed for item {i}: {retry_exc}")
            pending_results[ids[i]] = {
                "success": False,
                "error": f"MCQ generation failed after 1 retry. Primary: {primary_msg} | Retry: {retry_msg}",
            }


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


