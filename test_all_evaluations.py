"""
Test all evaluation async endpoints — DSA, AIML, SQL, DevOps, Cloud, Linux, Design.
Submits one request per competency, polls all in parallel until complete.

Usage:
  python3 test_all_evaluations.py
"""
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

GATEWAY = "http://localhost:7000"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
HEADERS = {"Content-Type": "application/json", "X-Api-Key": API_KEY}

# ── Test payloads ─────────────────────────────────────────────────────────────

TESTS = [
    {
        "name": "DSA",
        "endpoint": "/api/v1/evaluation/dsa/async",
        "payload": {
            "question_title": "Two Sum",
            "question_description": "Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.",
            "source_code": "def twoSum(nums, target):\n    seen = {}\n    for i, n in enumerate(nums):\n        diff = target - n\n        if diff in seen:\n            return [seen[diff], i]\n        seen[n] = i\n    return []",
            "language": "python",
            "total_passed": 8,
            "total_tests": 10,
            "public_passed": 5,
            "public_total": 6,
            "hidden_passed": 3,
            "hidden_total": 4,
            "test_results": [
                {"input": "[2,7,11,15], 9", "expected_output": "[0,1]", "user_output": "[0,1]", "passed": True, "hidden": False},
                {"input": "[3,2,4], 6", "expected_output": "[1,2]", "user_output": "[1,2]", "passed": True, "hidden": False},
                {"input": "[], 0", "expected_output": "[]", "user_output": "[]", "passed": False, "hidden": False},
            ],
        },
    },
    {
        "name": "AIML",
        "endpoint": "/api/v1/evaluation/aiml/async",
        "payload": {
            "question_title": "Iris Classification",
            "question_description": "Build a classifier for the Iris dataset using scikit-learn.",
            "source_code": "from sklearn.datasets import load_iris\nfrom sklearn.ensemble import RandomForestClassifier\nfrom sklearn.model_selection import train_test_split\nfrom sklearn.metrics import accuracy_score\n\ndata = load_iris()\nX, y = data.data, data.target\nX_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)\nclf = RandomForestClassifier(n_estimators=100, random_state=42)\nclf.fit(X_train, y_train)\npred = clf.predict(X_test)\nprint(f'Accuracy: {accuracy_score(y_test, pred):.4f}')",
            "language": "python",
            "total_passed": 4,
            "total_tests": 5,
            "public_passed": 3,
            "public_total": 3,
            "hidden_passed": 1,
            "hidden_total": 2,
            "test_results": [
                {"input": "iris dataset", "expected_output": "accuracy > 0.9", "user_output": "Accuracy: 1.0000", "passed": True, "hidden": False},
            ],
        },
    },
    {
        "name": "SQL",
        "endpoint": "/api/v1/evaluation/sql/async",
        "payload": {
            "question_id": "sql-test-001",
            "question_description": "Find all employees with salary greater than 50000",
            "user_query": "SELECT name, salary FROM employees WHERE salary > 50000 ORDER BY salary DESC",
            "reference_query": "SELECT name, salary FROM employees WHERE salary > 50000 ORDER BY salary DESC",
            "max_marks": 10,
            "schemas": {"employees": {"id": "INT", "name": "VARCHAR", "salary": "DECIMAL"}},
            "test_result": {
                "passed": True,
                "user_output": "[{\"name\": \"Alice\", \"salary\": 75000}]",
                "expected_output": "[{\"name\": \"Alice\", \"salary\": 75000}]",
                "error": None,
            },
            "difficulty": "easy",
            "use_cache": False,
        },
    },
    {
        "name": "DevOps",
        "endpoint": "/api/v1/evaluation/devops/async",
        "payload": {
            "question": {
                "id": "devops-test-001",
                "title": "Create S3 bucket with versioning",
                "description": "Configure an S3 bucket named aptor-logs with versioning enabled",
                "kind": "command",
                "difficulty": "medium",
                "instructions": "Create the bucket and enable versioning",
                "constraints": ["Use AWS CLI only"],
                "expected_submission_contains": ["versioning"],
                "expected_exit_code": 0,
                "expected_stdout_contains": ["Enabled"],
            },
            "submission": {
                "answer": "",
                "terminal_history": [
                    {"command": "aws s3api create-bucket --bucket aptor-logs", "output": "{\"Location\": \"/aptor-logs\"}"},
                    {"command": "aws s3api put-bucket-versioning --bucket aptor-logs --versioning-configuration Status=Enabled", "output": ""},
                    {"command": "aws s3api get-bucket-versioning --bucket aptor-logs", "output": "{\"Status\": \"Enabled\"}"},
                ],
                "engine_response": {"exit_code": 0, "stdout": "VersioningConfiguration: { Status: Enabled }", "stderr": ""},
                "validation_signals": {"passed": True, "question_score": 100, "max_score": 100, "reasons": ["stdout contains expected string"]},
            },
            "use_cache": False,
        },
    },
    {
        "name": "Cloud",
        "endpoint": "/api/v1/evaluation/cloud/async",
        "payload": {
            "question": {
                "id": "cloud-test-001",
                "title": "Configure IAM role for Lambda",
                "description": "Create an IAM role that allows Lambda to read from S3",
                "kind": "command",
                "difficulty": "medium",
                "instructions": "Create the IAM role with correct trust policy",
                "constraints": ["Use AWS CLI only"],
                "expected_submission_contains": ["lambda.amazonaws.com"],
                "expected_exit_code": 0,
                "expected_stdout_contains": ["RoleName"],
            },
            "submission": {
                "answer": "",
                "terminal_history": [
                    {"command": "aws iam create-role --role-name LambdaS3Role --assume-role-policy-document '{\"Version\":\"2012-10-17\",\"Statement\":[{\"Effect\":\"Allow\",\"Principal\":{\"Service\":\"lambda.amazonaws.com\"},\"Action\":\"sts:AssumeRole\"}]}'", "output": "{\"Role\": {\"RoleName\": \"LambdaS3Role\"}}"},
                    {"command": "aws iam attach-role-policy --role-name LambdaS3Role --policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess", "output": ""},
                ],
                "engine_response": {"exit_code": 0, "stdout": "RoleName: LambdaS3Role", "stderr": ""},
                "validation_signals": {"passed": True, "question_score": 100, "max_score": 100, "reasons": ["stdout contains RoleName"]},
            },
            "use_cache": False,
        },
    },
    {
        "name": "Linux",
        "endpoint": "/api/v1/evaluation/linux/async",
        "payload": {
            "question": {
                "id": "linux-test-001",
                "title": "Log Analysis and Process Management",
                "description": "Create incident dir, system.log, filter errors, count them, list and stop processes",
                "kind": "command",
                "difficulty": "medium",
                "instructions": "Create directory, file, add log entries, filter errors, count, list processes, stop PID 102",
                "constraints": ["Use standard Linux commands"],
                "expected_submission_contains": ["errors.log"],
                "expected_exit_code": 0,
            },
            "submission": {
                "answer": "",
                "terminal_history": [
                    {"command": "mkdir incident", "output": ""},
                    {"command": "cd incident && touch system.log", "output": ""},
                    {"command": "echo 'ERROR Disk failure' >> system.log && echo 'INFO Server started' >> system.log && echo 'ERROR Memory leak' >> system.log", "output": ""},
                    {"command": "grep ERROR system.log > errors.log", "output": ""},
                    {"command": "cat errors.log", "output": "ERROR Disk failure\nERROR Memory leak"},
                    {"command": "grep ERROR system.log | wc -l", "output": "2"},
                    {"command": "ps aux", "output": "PID TTY CMD\n101 pts/0 bash\n102 pts/0 python"},
                    {"command": "kill 102", "output": ""},
                ],
                "engine_response": {"exit_code": 0, "stdout": "", "stderr": ""},
                "validation_signals": {"passed": True, "question_score": 100, "max_score": 100, "reasons": ["all tasks completed"]},
            },
            "use_cache": False,
        },
    },
    {
        "name": "DataEng",
        "endpoint": "/api/v1/evaluation/data-engineering/async",
        "payload": {
            "question": {
                "id": "de-test-001",
                "title": "PySpark GroupBy Aggregation",
                "description": "Given a DataFrame of sales records with columns (region, amount), compute the total sales amount per region.",
                "question_type": "coding",
                "difficulty": "medium",
                "rubric_items": [
                    "use groupBy on region column",
                    "aggregate sum of amount",
                    "return result as DataFrame",
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
                    "spark = SparkSession.builder.appName('test').getOrCreate()\n"
                    "rows = input_data.get('rows', [])\n"
                    "df = spark.createDataFrame(rows)\n"
                    "result = df.groupBy('region').agg(_sum('amount').alias('total'))\n"
                    "result_df = [row.asDict() for row in result.collect()]\n"
                ),
                "answer": "",
                "execution_results": [],
            },
            "use_cache": False,
        },
    },
    {
        "name": "DataEngSubj",
        "endpoint": "/api/v1/evaluation/data-engineering/async",
        "payload": {
            "question": {
                "id": "de-test-002",
                "title": "Explain PySpark Partitioning",
                "description": "Describe how partitioning works in PySpark and its impact on performance.",
                "question_type": "subjective",
                "difficulty": "medium",
                "rubric_items": [
                    "partitioning distributes data across nodes for parallel processing",
                    "repartition increases partitions, coalesce reduces them",
                    "partition count affects parallelism and performance",
                    "data skew causes uneven partitions and latency",
                ],
                "test_cases": [],
            },
            "submission": {
                "code": "",
                "answer": (
                    "PySpark partitioning distributes data across executor nodes to enable parallel processing. "
                    "You can use repartition() to increase the number of partitions or coalesce() to reduce them without a full shuffle. "
                    "The partition count directly affects parallelism and throughput — too few partitions underutilise the cluster, "
                    "while too many cause scheduling overhead. Data skew, where some partitions are much larger than others, "
                    "leads to latency because slow tasks block the stage. Monitoring partition sizes and using partitioning strategies "
                    "like salting helps with governance and schema quality in production pipelines."
                ),
                "execution_results": [],
            },
            "use_cache": False,
        },
    },
    {
        "name": "Design",
        "endpoint": "/api/v1/evaluation/design/async",
        "payload": {
            "question": {
                "id": "design-test-001",
                "title": "E-commerce Homepage Design",
                "description": "Design a responsive homepage for an e-commerce platform",
                "role": "UI/UX Designer",
                "difficulty": "intermediate",
                "deliverables": ["Homepage", "Mobile view", "Component library"],
                "constraints": ["Use 2-3 brand colors", "WCAG AA compliance", "Grid system required"],
            },
            "submission": {
                "design_metrics": {
                    "total_elements": 45,
                    "pages": 3,
                    "colors_used": 3,
                    "typography_scales": 4,
                    "components": 12,
                    "reusable_components": 8,
                    "has_grid": True,
                    "has_tokens": True,
                    "color_palette_size": 3,
                    "deliverables_found": ["Homepage", "Mobile view", "Component library"],
                    "deliverables_missing": [],
                },
                "screenshot_available": False,
            },
            "use_cache": False,
        },
    },
]


def submit_job(test: dict) -> dict:
    resp = requests.post(
        f"{GATEWAY}{test['endpoint']}",
        headers=HEADERS,
        json=test["payload"],
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    return {"name": test["name"], "job_id": data["job_id"]}


def poll_job(job_info: dict, timeout: int = 2000) -> dict:
    name = job_info["name"]
    job_id = job_info["job_id"]
    deadline = time.time() + timeout
    t_start = time.time()

    while time.time() < deadline:
        try:
            resp = requests.get(f"{GATEWAY}/api/v1/job/{job_id}", headers=HEADERS, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            status = data.get("status")
            if status == "complete":
                elapsed = time.time() - t_start
                result = data.get("result", {})
                score = result.get("overall_score", "N/A")
                return {"name": name, "job_id": job_id, "score": score, "elapsed": elapsed, "error": None, "result": result}
            if status == "failed":
                return {"name": name, "job_id": job_id, "score": None, "elapsed": time.time() - t_start, "error": data.get("error", "failed"), "result": None}
        except Exception:
            pass
        time.sleep(5)

    return {"name": name, "job_id": job_id, "score": None, "elapsed": timeout, "error": f"Timed out after {timeout}s", "result": None}


def main():
    print("=" * 60)
    print("Testing ALL evaluation async endpoints")
    print("=" * 60)
    t_start = time.time()

    # Submit all in parallel
    print("\nSubmitting jobs...\n")
    jobs = []
    with ThreadPoolExecutor(max_workers=len(TESTS)) as ex:
        futures = {ex.submit(submit_job, t): t["name"] for t in TESTS}
        for future in as_completed(futures):
            name = futures[future]
            try:
                job = future.result()
                jobs.append(job)
                print(f"  ✓ {job['name']:10s} → job_id: {job['job_id']}")
            except Exception as e:
                print(f"  ✗ {name:10s} → SUBMIT FAILED: {e}")

    print(f"\nAll {len(jobs)} jobs submitted in {time.time() - t_start:.1f}s")
    print("\nPolling all jobs in parallel...\n")

    # Poll all in parallel
    results = []
    with ThreadPoolExecutor(max_workers=len(jobs)) as ex:
        futures = {ex.submit(poll_job, job): job["name"] for job in jobs}
        for future in as_completed(futures):
            r = future.result()
            if r["error"]:
                print(f"  ✗ {r['name']:10s}: ERROR — {r['error']} ({r['elapsed']:.1f}s)")
            else:
                # Show key score fields per competency
                result = r["result"] or {}
                extra = ""
                if r["name"] == "SQL":
                    pct = result.get("percentage", "N/A")
                    extra = f" | percentage={pct}%"
                elif r["name"] == "Design":
                    rule = result.get("rule_score", "N/A")
                    qwen = result.get("qwen_score", "N/A")
                    extra = f" | rule={rule} qwen={qwen}"
                elif r["name"] in ("DSA", "AIML"):
                    one_liner = result.get("one_liner", "")[:50]
                    extra = f" | {one_liner}"
                print(f"  ✓ {r['name']:10s}: score={r['score']}/100{extra} ({r['elapsed']:.1f}s)")

                # Print full result
                import json
                print(f"\n  Full result for {r['name']}:")
                print(json.dumps(result, indent=4, default=str))
                print()

            results.append(r)

    total = time.time() - t_start
    success = sum(1 for r in results if not r["error"])

    print(f"\n{'=' * 60}")
    print(f"Results:    {success}/{len(results)} succeeded")
    print(f"Total time: {total:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
