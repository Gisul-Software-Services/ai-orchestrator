"""
Standalone test for data engineering evaluator — deterministic layers only.
No vLLM, no Redis, no server needed.

Run from workspace root:
    python test_de_eval_logic.py
"""
import sys
import math

sys.path.insert(0, ".")

from backend.model_app.evaluation.data_engineering_evaluator import (
    _normalize_cell,
    _compare_dataframes,
    _run_static_partial_credit,
    _run_subjective_rubric,
    _resolve_final_score,
    _check_security,
    _FALLBACK_REASONS,
)

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
errors = []

def check(label, condition, got=None):
    if condition:
        print(f"  {PASS} {label}")
    else:
        print(f"  {FAIL} {label}  →  got: {got}")
        errors.append(label)

# ─────────────────────────────────────────────────────────────
print("\n── _normalize_cell ──")
check("None → None",           _normalize_cell(None) is None)
check("NaN → None",            _normalize_cell(float("nan")) is None)
check("3.0 → 3 (int)",         _normalize_cell(3.0) == 3 and isinstance(_normalize_cell(3.0), int))
check("3.5 stays float",       _normalize_cell(3.5) == 3.5)
check("' foo ' → 'foo'",       _normalize_cell("  foo  ") == "foo")
check("True → True (bool)",    _normalize_cell(True) is True)
check("False → False (bool)",  _normalize_cell(False) is False)
check("42 (int) unchanged",    _normalize_cell(42) == 42)

# ─────────────────────────────────────────────────────────────
print("\n── _compare_dataframes ──")

# Exact match
r = _compare_dataframes([{"a": 1, "b": "x"}], [{"a": 1, "b": "x"}])
check("exact match → score=100, is_correct=True", r["deterministic_score"] == 100.0 and r["is_correct"])

# Schema mismatch
r = _compare_dataframes([{"a": 1, "c": 2}], [{"a": 1, "b": 2}])
check("schema mismatch → score≤40", r["deterministic_score"] <= 40.0, r["deterministic_score"])
check("schema mismatch → is_correct=False", not r["is_correct"])

# Row count mismatch
r = _compare_dataframes([{"a": 1}, {"a": 2}], [{"a": 1}])
check("row count mismatch → score≤60", r["deterministic_score"] <= 60.0, r["deterministic_score"])

# Data mismatch (same schema, same count, wrong values)
r = _compare_dataframes([{"a": 1, "b": 9}], [{"a": 1, "b": 2}])
check("data mismatch → score≤85", r["deterministic_score"] <= 85.0, r["deterministic_score"])

# Order-agnostic match
r = _compare_dataframes(
    [{"a": 2, "b": "y"}, {"a": 1, "b": "x"}],
    [{"a": 1, "b": "x"}, {"a": 2, "b": "y"}],
)
check("order-agnostic match → score=100", r["deterministic_score"] == 100.0, r["deterministic_score"])

# Float normalisation in comparison
r = _compare_dataframes([{"v": 3.0}], [{"v": 3}])
check("3.0 == 3 in comparison → score=100", r["deterministic_score"] == 100.0, r["deterministic_score"])

# ─────────────────────────────────────────────────────────────
print("\n── _run_static_partial_credit ──")

question = {"title": "PySpark groupBy aggregation", "description": "Use groupBy and agg to count rows"}

# All 8 patterns present
all_patterns_code = """
from pyspark.sql import SparkSession
from pyspark.sql.types import StructType, StructField
from pyspark.sql.functions import col, when, otherwise, fillna

spark = SparkSession.builder.appName("test").getOrCreate()
df = spark.read.csv("data.csv")
df2 = df.withColumn("x", when(col("a") > 0, 1).otherwise(0))
df3 = df2.groupBy("x").agg({"b": "count", "c": "sum"})
spark.sql("SELECT * FROM t")
df3.write.save("out")
"""
score = _run_static_partial_credit(question, {"code": all_patterns_code})
check("all 8 patterns → score ≤ 40", score <= 40.0, score)
check("all 8 patterns → score ≥ 24 (pattern pts)", score >= 24.0, score)

# Empty code
score = _run_static_partial_credit(question, {"code": ""})
check("empty code → score=0", score == 0.0, score)

# No patterns
score = _run_static_partial_credit(question, {"code": "x = 1 + 1"})
check("no patterns → score ≥ 0 and ≤ 40", 0.0 <= score <= 40.0, score)

# ─────────────────────────────────────────────────────────────
print("\n── _run_subjective_rubric ──")

question_subj = {
    "title": "Explain PySpark partitioning",
    "description": "Describe how partitioning works in PySpark",
    "rubric_items": [
        "partitioning distributes data across nodes",
        "use repartition or coalesce to control partitions",
        "partitioning affects performance and parallelism",
    ],
}

# Short answer penalty
score = _run_subjective_rubric(question_subj, {"answer": "PySpark uses partitions."})
check("< 20 words → score ≤ 10", score <= 10.0, score)

# Good answer
good_answer = (
    "PySpark partitioning distributes data across nodes for parallel processing. "
    "You can use repartition to increase partitions or coalesce to reduce them. "
    "Partitioning affects performance because it controls parallelism and data locality. "
    "Poor partitioning leads to latency and throughput issues. "
    "Monitoring partition sizes helps with governance and schema quality."
)
score = _run_subjective_rubric(question_subj, {"answer": good_answer})
check("good answer → score > 35", score > 35.0, score)
check("good answer → score ≤ 100", score <= 100.0, score)

# Copy-paste detection
copy_answer = "Explain PySpark partitioning Describe how partitioning works in PySpark partitioning distributes"
score = _run_subjective_rubric(question_subj, {"answer": copy_answer})
check("copy-paste → score ≤ 22", score <= 22.0, score)

# ─────────────────────────────────────────────────────────────
print("\n── _resolve_final_score ──")

# Default: deterministic wins
final, reason = _resolve_final_score(75.0, 30.0, 60.0, "data_mismatch")
check("default → final=det_score=75", final == 75.0, final)

# AI fallback: det=0, reason in FALLBACK_REASONS
final, reason = _resolve_final_score(0.0, 20.0, 55.0, "failed")
check("AI fallback → final=ai_score=55", final == 55.0, final)
check("AI fallback → reason contains 'ai_fallback'", "ai_fallback" in reason, reason)

# Static override: static > ai
final, reason = _resolve_final_score(0.0, 35.0, 20.0, "failed")
check("static override → final=static=35", final == 35.0, final)
check("static override → reason='static_partial_credit'", reason == "static_partial_credit", reason)

# Clamping
final, _ = _resolve_final_score(150.0, 0.0, None, "exact_match")
check("clamp above 100 → 100", final == 100.0, final)
final, _ = _resolve_final_score(-10.0, 0.0, None, "exact_match")
check("clamp below 0 → 0", final == 0.0, final)

# ─────────────────────────────────────────────────────────────
print("\n── _check_security ──")

check("import os → blocked",        _check_security("import os") is not None)
check("import sys → blocked",       _check_security("import sys") is not None)
check("from subprocess import run → blocked", _check_security("from subprocess import run") is not None)
check("from socket import socket → blocked",  _check_security("from socket import socket") is not None)
check("import shutil → blocked",    _check_security("import shutil") is not None)
check("import pyspark → allowed",   _check_security("import pyspark") is None)
check("from pyspark.sql import SparkSession → allowed",
      _check_security("from pyspark.sql import SparkSession") is None)

# ─────────────────────────────────────────────────────────────
print()
if errors:
    print(f"\033[91m{len(errors)} test(s) FAILED:\033[0m")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)
else:
    total = 30
    print(f"\033[92mAll tests passed!\033[0m")
