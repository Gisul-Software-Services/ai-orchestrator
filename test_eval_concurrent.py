"""
Test 10 concurrent DevOps evaluation requests via the async endpoint.
Fires all 10 at once, then polls ALL jobs in parallel until all complete.

Usage:
  python3 test_eval_concurrent.py
"""
import json
import time
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

GATEWAY = "http://localhost:7000"
API_KEY = "adm_7DO6mYfMDUvUayUCfx-jGlwUWnzH5PVXtnAwYEMTS9IhhCwg"
HEADERS = {
    "Content-Type": "application/json",
    "X-Api-Key": API_KEY,
}

# 10 different DevOps questions to avoid cache hits
QUESTIONS = [
    {
        "id": f"devops-test-{i:03d}",
        "title": f"Test question {i}",
        "description": f"Configure S3 bucket test-bucket-{i} with versioning enabled",
        "instructions": "Create the bucket and enable versioning",
        "constraints": ["Use AWS CLI only"],
        "expected_submission_contains": ["versioning"],
        "expected_exit_code": 0,
        "expected_stdout_contains": ["Enabled"],
    }
    for i in range(1, 11)
]

SUBMISSION = {
    "answer": "",
    "terminal_history": [
        {"command": "aws s3api create-bucket --bucket test-bucket", "output": '{"Location": "/test-bucket"}'},
        {"command": "aws s3api put-bucket-versioning --bucket test-bucket --versioning-configuration Status=Enabled", "output": ""},
        {"command": "aws s3api get-bucket-versioning --bucket test-bucket", "output": '{"Status": "Enabled"}'},
    ],
    "outputs": ['{"Status": "Enabled"}'],
    "engine_response": {"exit_code": 0, "stdout": "VersioningConfiguration: { Status: Enabled }", "stderr": ""},
    "validation_signals": {"passed": True, "question_score": 100, "max_score": 100, "reasons": ["stdout contains expected string"]},
}


def submit_job(question: dict) -> dict:
    """Submit one async evaluation request, return {question_id, job_id}."""
    payload = {"question": question, "submission": SUBMISSION, "use_cache": False}
    resp = requests.post(f"{GATEWAY}/api/v1/evaluation/devops/async", headers=HEADERS, json=payload, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return {"question_id": question["id"], "job_id": data["job_id"]}


def poll_single_job(job_info: dict, timeout: int = 1600) -> dict:
    """Poll a single job until complete. Returns result dict."""
    question_id = job_info["question_id"]
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
                tasks_done = result.get("task_completion", {}).get("completed", "?")
                tasks_total = result.get("task_completion", {}).get("total", "?")
                return {
                    "question_id": question_id,
                    "job_id": job_id,
                    "score": score,
                    "tasks": f"{tasks_done}/{tasks_total}",
                    "elapsed": elapsed,
                    "error": None,
                }
            if status == "failed":
                return {
                    "question_id": question_id,
                    "job_id": job_id,
                    "score": None,
                    "tasks": None,
                    "elapsed": time.time() - t_start,
                    "error": data.get("error", "job failed"),
                }
        except Exception as e:
            pass  # transient error, keep polling
        time.sleep(5)

    return {
        "question_id": question_id,
        "job_id": job_id,
        "score": None,
        "tasks": None,
        "elapsed": timeout,
        "error": f"Timed out after {timeout}s",
    }


def main():
    print(f"Submitting 10 concurrent DevOps evaluation requests...\n")
    t_start = time.time()

    # Step 1 — Submit all 10 in parallel
    jobs = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(submit_job, q): q["id"] for q in QUESTIONS}
        for future in as_completed(futures):
            try:
                result = future.result()
                jobs.append(result)
                print(f"  ✓ Submitted {result['question_id']} → job_id: {result['job_id']}")
            except Exception as e:
                print(f"  ✗ Submit failed for {futures[future]}: {e}")

    submit_time = time.time() - t_start
    print(f"\nAll {len(jobs)} jobs submitted in {submit_time:.1f}s")
    print(f"Polling ALL jobs in parallel (Qwen processes one at a time internally)...\n")

    # Step 2 — Poll ALL jobs in parallel — don't wait for one before checking others
    results = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(poll_single_job, job): job["question_id"] for job in jobs}
        for future in as_completed(futures):
            result = future.result()
            if result["error"]:
                print(f"  ✗ {result['question_id']}: ERROR — {result['error']} ({result['elapsed']:.1f}s)")
            else:
                print(f"  ✓ {result['question_id']}: score={result['score']}/100, tasks={result['tasks']} ({result['elapsed']:.1f}s)")
            results.append(result)

    total_time = time.time() - t_start
    success = sum(1 for r in results if not r["error"])
    avg_score = sum(r["score"] for r in results if r["score"] is not None) / max(success, 1)

    print(f"\n{'='*55}")
    print(f"Results:      {success}/{len(results)} succeeded")
    print(f"Avg score:    {avg_score:.1f}/100")
    print(f"Total time:   {total_time:.1f}s")
    print(f"Submit time:  {submit_time:.1f}s (all jobs queued)")
    print(f"Process time: {total_time - submit_time:.1f}s (Qwen processing)")


if __name__ == "__main__":
    main()
