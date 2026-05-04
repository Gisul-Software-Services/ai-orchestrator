"""
Focused test for the data engineering evaluation endpoint.
Tests both coding and subjective question types.

Run from WSL:
    python3 test_de_endpoint.py
"""
import json
import time
import requests

GATEWAY = "http://localhost:7000"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
BOLD  = "\033[1m"


def poll(job_id: str, timeout: int = 300) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{GATEWAY}/api/v1/job/{job_id}", headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        status = data.get("status")
        if status == "complete":
            return data.get("result", {})
        if status == "failed":
            raise RuntimeError(f"Job failed: {data.get('error')}")
        print(f"  ... status={status}, waiting 5s")
        time.sleep(5)
    raise TimeoutError(f"Job {job_id} did not complete in {timeout}s")


def run_test(name: str, payload: dict) -> None:
    print(f"\n{BOLD}{'─'*55}{RESET}")
    print(f"{BOLD}TEST: {name}{RESET}")
    print(f"{'─'*55}")

    # ── Submit ────────────────────────────────────────────────
    print("Submitting...")
    try:
        r = requests.post(
            f"{GATEWAY}/api/v1/evaluation/data-engineering/async",
            headers=HEADERS,
            json=payload,
            timeout=15,
        )
        if r.status_code != 200:
            print(f"{RED}✗ Submit failed {r.status_code}: {r.text[:500]}{RESET}")
            return
        job_id = r.json()["job_id"]
        print(f"  job_id: {job_id}")
    except Exception as e:
        print(f"{RED}✗ Submit error: {e}{RESET}")
        return

    # ── Poll ──────────────────────────────────────────────────
    print("Polling for result...")
    t0 = time.time()
    try:
        result = poll(job_id)
    except Exception as e:
        print(f"{RED}✗ Poll error: {e}{RESET}")
        return
    elapsed = time.time() - t0

    # ── Print result ──────────────────────────────────────────
    print(f"\n{GREEN}✓ Completed in {elapsed:.1f}s{RESET}")
    print(f"\n  final_score:          {result.get('final_score')}")
    print(f"  deterministic_score:  {result.get('deterministic_score')}")
    print(f"  static_partial_score: {result.get('static_partial_score')}")
    print(f"  ai_score:             {result.get('ai_score')}")
    print(f"  score_reason:         {result.get('score_reason')}")
    print(f"  is_correct:           {result.get('is_correct')}")

    per_tc = result.get("per_test_case_results", [])
    if per_tc:
        print(f"\n  per_test_case_results:")
        for tc in per_tc:
            print(f"    [{tc.get('test_case_index')}] status={tc.get('status')} "
                  f"score={tc.get('deterministic_score')} "
                  f"reason={tc.get('score_reason')} "
                  f"error={str(tc.get('error_message') or '')[:80]}")

    ai = result.get("ai_feedback", {})
    if ai:
        print(f"\n  ai_feedback.overall_score:       {ai.get('overall_score')}")
        print(f"  ai_feedback.correctness:         {str(ai.get('correctness_feedback',''))[:80]}")
        print(f"  ai_feedback.strengths:           {ai.get('strengths', [])[:2]}")
        print(f"  ai_feedback.improvement:         {ai.get('improvement_suggestions', [])[:2]}")

    print(f"\n  Full JSON:")
    print(json.dumps(result, indent=4, default=str))


# ─────────────────────────────────────────────────────────────
# Test 1: Coding — correct PySpark groupBy
# ─────────────────────────────────────────────────────────────
CODING_CORRECT = {
    "question": {
        "id": "de-coding-001",
        "title": "PySpark GroupBy Aggregation",
        "description": "Given a DataFrame of sales records with columns (region, amount), compute total sales per region.",
        "question_type": "coding",
        "difficulty": "medium",
        "rubric_items": [
            "use groupBy on region column",
            "aggregate sum of amount",
            "return result as list of dicts",
        ],
        "test_cases": [
            {
                "input_data": {
                    "rows": [
                        {"region": "North", "amount": 100},
                        {"region": "South", "amount": 200},
                        {"region": "North", "amount": 150},
                    ]
                },
                "expected_output": [
                    {"region": "North", "total": 250},
                    {"region": "South", "total": 200},
                ],
            }
        ],
    },
    "submission": {
        "code": (
            "from pyspark.sql import SparkSession\n"
            "from pyspark.sql.functions import sum as _sum\n\n"
            "spark = SparkSession.builder.master('local').appName('test').getOrCreate()\n"
            "rows = input_data.get('rows', [])\n"
            "df = spark.createDataFrame(rows)\n"
            "result = df.groupBy('region').agg(_sum('amount').alias('total'))\n"
            "result_df = [row.asDict() for row in result.collect()]\n"
        ),
        "answer": "",
        # Execution engine ran the code and sends back these results
        "execution_results": [
            {
                "test_case_index": 0,
                "status": "success",
                "output_df": [
                    {"region": "North", "total": 250},
                    {"region": "South", "total": 200},
                ],
                "error_message": None,
            }
        ],
    },
    "use_cache": False,
}

# ─────────────────────────────────────────────────────────────
# Test 2: Coding — wrong output (data mismatch)
# ─────────────────────────────────────────────────────────────
CODING_WRONG = {
    "question": {
        "id": "de-coding-002",
        "title": "PySpark GroupBy Aggregation",
        "description": "Compute total sales per region.",
        "question_type": "coding",
        "difficulty": "medium",
        "rubric_items": ["use groupBy", "aggregate sum"],
        "test_cases": [
            {
                "input_data": {"rows": [{"region": "North", "amount": 100}]},
                "expected_output": [{"region": "North", "total": 100}],
            }
        ],
    },
    "submission": {
        # Execution engine ran the code — returned wrong column name
        "code": "result_df = [{'region': r['region'], 'wrong_col': r['amount']} for r in rows]",
        "answer": "",
        "execution_results": [
            {
                "test_case_index": 0,
                "status": "success",
                "output_df": [{"region": "North", "wrong_col": 100}],  # wrong column
                "error_message": None,
            }
        ],
    },
    "use_cache": False,
}

# ─────────────────────────────────────────────────────────────
# Test 3: Coding — execution fails (static partial credit)
# ─────────────────────────────────────────────────────────────
CODING_FAIL = {
    "question": {
        "id": "de-coding-003",
        "title": "PySpark Null Handling",
        "description": "Use fillna and groupBy to aggregate data with null values.",
        "question_type": "coding",
        "difficulty": "medium",
        "rubric_items": ["use fillna to handle nulls", "use groupBy aggregation"],
        "test_cases": [
            {
                "input_data": {"rows": [{"a": 1}]},
                "expected_output": [{"a": 1}],
            }
        ],
    },
    "submission": {
        # Execution engine ran the code — it failed (file not found)
        "code": (
            "from pyspark.sql import SparkSession\n"
            "from pyspark.sql.functions import col, when, otherwise\n"
            "spark = SparkSession.builder.master('local').appName('test').getOrCreate()\n"
            "df = spark.read.parquet('nonexistent')\n"
            "df2 = df.fillna(0).groupBy('a').agg({'b': 'sum'})\n"
            "df3 = df2.withColumn('x', when(col('a') > 0, 1).otherwise(0))\n"
            "result_df = [row.asDict() for row in df3.collect()]\n"
        ),
        "answer": "",
        "execution_results": [
            {
                "test_case_index": 0,
                "status": "failed",
                "output_df": None,
                "error_message": "AnalysisException: Path does not exist: nonexistent",
            }
        ],
    },
    "use_cache": False,
}

# ─────────────────────────────────────────────────────────────
# Test 4: Subjective — good answer
# ─────────────────────────────────────────────────────────────
SUBJECTIVE_GOOD = {
    "question": {
        "id": "de-subj-001",
        "title": "Explain PySpark Partitioning",
        "description": "Describe how partitioning works in PySpark and its impact on performance.",
        "question_type": "subjective",
        "difficulty": "medium",
        "rubric_items": [
            "partitioning distributes data across nodes for parallel processing",
            "repartition increases partitions, coalesce reduces them without full shuffle",
            "partition count affects parallelism and throughput",
            "data skew causes uneven partitions and latency",
        ],
        "test_cases": [],
    },
    "submission": {
        "code": "",
        "answer": (
            "PySpark partitioning distributes data across executor nodes to enable parallel processing. "
            "You can use repartition() to increase the number of partitions or coalesce() to reduce them "
            "without a full shuffle, which is more efficient. The partition count directly affects parallelism "
            "and throughput — too few partitions underutilise the cluster, while too many cause scheduling overhead. "
            "Data skew, where some partitions are much larger than others, leads to latency because slow tasks "
            "block the stage. Monitoring partition sizes and using partitioning strategies like salting helps "
            "with governance and schema quality in production pipelines. Checkpointing can also help with "
            "lineage tracking and rollback in long-running jobs."
        ),
        "execution_results": [],
    },
    "use_cache": False,
}


if __name__ == "__main__":
    print(f"\n{BOLD}Data Engineering Evaluation — Endpoint Tests{RESET}")
    print(f"Gateway: {GATEWAY}")

    run_test("Coding — correct output (expect score ~100)", CODING_CORRECT)
    run_test("Coding — wrong column name (expect score ≤40)", CODING_WRONG)
    run_test("Coding — execution fails (expect static partial credit)", CODING_FAIL)
    run_test("Subjective — good answer (expect score >50)", SUBJECTIVE_GOOD)

    print(f"\n{BOLD}{'='*55}{RESET}")
    print("Done.")
