"""
enrich_dsa.py — v3.1
====================
Dataset-driven enrichment using LeetCodeDataset-train.jsonl.

Test cases — from dataset directly (100% accurate):
  Simple inputs  → public_testcases  (4 cases)
  Edge cases     → hidden_testcases  (8 cases)
  Total: 12 test cases per problem

Qwen generates ONLY:
  function_signature (name, parameters, return_type)
  starter_code for 10 languages

Fields KEPT in output:
  title, task_id, question_id, difficulty, tags
  problem_description, entry_point
  completion (correct Python solution)
  starter_code original (Python)
  function_signature (Qwen generated)
  starter_code 10 languages (Qwen generated)
  public_testcases, hidden_testcases
  pipeline, test_case_source

Fields REMOVED from output (too large / not needed):
  prompt, test, response, query, estimated_date, input_output (raw)
"""

import json
import requests
import time
import os

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE    = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\LeetCodeDataset-train.jsonl"
OUTPUT_FILE   = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\dsa_enriched.json"
API_URL       = "http://localhost:9000/api/v1/enrich-dsa"
DELAY_SECONDS = 2
TIMEOUT       = 120

# Fields to keep from original dataset
KEEP_FIELDS = {
    "title",
    "task_id",
    "question_id",
    "difficulty",
    "tags",
    "problem_description",
    "entry_point",
    "completion",       # correct Python solution — keep for future use
    "starter_code",     # original Python starter — keep as reference
}

# Fields to explicitly remove (large blobs not needed)
REMOVE_FIELDS = {
    "prompt",
    "test",
    "response",
    "query",
    "estimated_date",
    "input_output",     # replaced by public_testcases + hidden_testcases
}
# ──────────────────────────────────────────────────────────────────────────────

def filter_problem_fields(problem: dict) -> dict:
    """
    Returns a clean version of the problem with only needed fields.
    Removes large blobs that are not needed in the enriched output.
    """
    return {k: v for k, v in problem.items() if k in KEEP_FIELDS}


# Load all problems from JSONL
problems = []
with open(INPUT_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            problems.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping bad line: {e}")

print(f"📚 Total problems loaded: {len(problems)}")

# Load already enriched (resume support)
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        enriched = json.load(f)
    done_ids = {str(p.get("question_id", p.get("task_id", ""))) for p in enriched}
    print(f"▶️  Resuming — {len(enriched)} already done, {len(problems) - len(enriched)} remaining")
else:
    enriched = []
    done_ids = set()
    print("🆕 Starting fresh")

success_count = 0
fail_count    = 0
skip_count    = 0

print("\n" + "=" * 60)

for i, problem in enumerate(problems):
    pid   = str(problem.get("question_id", problem.get("task_id", i)))
    title = problem.get("task_id", f"Problem {i}")

    # Skip already done
    if pid in done_ids:
        skip_count += 1
        continue

    # Skip if no input_output data
    if not problem.get("input_output"):
        print(f"[{i+1}/{len(problems)}] ⏭️  Skipped (no input_output): {title}")
        skip_count += 1
        continue

    difficulty = problem.get("difficulty", "?")
    print(f"[{i+1}/{len(problems)}] ⚙️  Enriching: {title} ({difficulty})...")

    try:
        resp = requests.post(API_URL, json=problem, timeout=TIMEOUT)

        if resp.status_code == 200:
            result = resp.json()

            # Start with only the clean filtered fields
            enriched_problem = filter_problem_fields(problem)

            # Add enriched fields from Qwen + parsed test cases
            enriched_problem["function_signature"] = result.get("function_signature", {})
            enriched_problem["public_testcases"]   = result.get("public_testcases", [])
            enriched_problem["hidden_testcases"]   = result.get("hidden_testcases", [])
            enriched_problem["starter_code_langs"] = result.get("starter_code", {})
            enriched_problem["pipeline"]           = result.get("pipeline", "dataset_driven")
            enriched_problem["test_case_source"]   = result.get("test_case_source", "leetcode_dataset")

            enriched.append(enriched_problem)
            done_ids.add(pid)
            success_count += 1

            # Save after every problem — crash-safe
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=2, ensure_ascii=False)

            sig_name = result.get("function_signature", {}).get("name", "?")
            n_public = len(result.get("public_testcases", []))
            n_hidden = len(result.get("hidden_testcases", []))
            n_langs  = len(result.get("starter_code", {}))
            print(f"         ✅ fn={sig_name}, public={n_public}, hidden={n_hidden}, langs={n_langs}")

        else:
            fail_count += 1
            print(f"         ❌ HTTP {resp.status_code}: {resp.text[:200]}")

    except requests.exceptions.Timeout:
        fail_count += 1
        print(f"         ⏱️  Timeout after {TIMEOUT}s — skipping")

    except Exception as e:
        fail_count += 1
        print(f"         ❌ Error: {e}")

    if (i + 1) % 50 == 0:
        print(f"\n── Progress: {len(enriched)}/{len(problems)} done | "
              f"✅ {success_count} | ❌ {fail_count} | ⏭️ {skip_count} ──\n")

    time.sleep(DELAY_SECONDS)

print("\n" + "=" * 60)
print(f"✅ Enrichment complete!")
print(f"   Total enriched  : {len(enriched)}")
print(f"   Success         : {success_count}")
print(f"   Failed          : {fail_count}")
print(f"   Skipped         : {skip_count}")
print(f"   Output file     : {OUTPUT_FILE}")"""
enrich_dsa.py — v3.1
====================
Dataset-driven enrichment using LeetCodeDataset-train.jsonl.

Test cases — from dataset directly (100% accurate):
  Simple inputs  → public_testcases  (4 cases)
  Edge cases     → hidden_testcases  (8 cases)
  Total: 12 test cases per problem

Qwen generates ONLY:
  function_signature (name, parameters, return_type)
  starter_code for 10 languages

Fields KEPT in output:
  title, task_id, question_id, difficulty, tags
  problem_description, entry_point
  completion (correct Python solution)
  starter_code original (Python)
  function_signature (Qwen generated)
  starter_code 10 languages (Qwen generated)
  public_testcases, hidden_testcases
  pipeline, test_case_source

Fields REMOVED from output (too large / not needed):
  prompt, test, response, query, estimated_date, input_output (raw)
"""
import json
import requests
import time
import os

# ── Config ────────────────────────────────────────────────────────────────────
INPUT_FILE    = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\LeetCodeDataset-train.jsonl"
OUTPUT_FILE   = r"C:\Users\adity\Documents\Gisul\gisul_model\assests\dsa-coding\dsa_enriched.json"
API_URL       = "http://localhost:9000/api/v1/enrich-dsa"
DELAY_SECONDS = 2
TIMEOUT       = 120

# Fields to keep from original dataset
KEEP_FIELDS = {
    "title",
    "task_id",
    "question_id",
    "difficulty",
    "tags",
    "problem_description",
    "entry_point",
    "completion",       # correct Python solution — keep for future use
    "starter_code",     # original Python starter — keep as reference
}

# Fields to explicitly remove (large blobs not needed)
REMOVE_FIELDS = {
    "prompt",
    "test",
    "response",
    "query",
    "estimated_date",
    "input_output",     # replaced by public_testcases + hidden_testcases
}
# ──────────────────────────────────────────────────────────────────────────────

def filter_problem_fields(problem: dict) -> dict:
    """
    Returns a clean version of the problem with only needed fields.
    Removes large blobs that are not needed in the enriched output.
    """
    return {k: v for k, v in problem.items() if k in KEEP_FIELDS}


# Load all problems from JSONL
problems = []
with open(INPUT_FILE, encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            problems.append(json.loads(line))
        except json.JSONDecodeError as e:
            print(f"⚠️  Skipping bad line: {e}")

print(f"📚 Total problems loaded: {len(problems)}")

# Load already enriched (resume support)
if os.path.exists(OUTPUT_FILE):
    with open(OUTPUT_FILE, encoding="utf-8") as f:
        enriched = json.load(f)
    done_ids = {str(p.get("question_id", p.get("task_id", ""))) for p in enriched}
    print(f"▶️  Resuming — {len(enriched)} already done, {len(problems) - len(enriched)} remaining")
else:
    enriched = []
    done_ids = set()
    print("🆕 Starting fresh")

success_count = 0
fail_count    = 0
skip_count    = 0

print("\n" + "=" * 60)

for i, problem in enumerate(problems):
    pid   = str(problem.get("question_id", problem.get("task_id", i)))
    title = problem.get("task_id", f"Problem {i}")

    # Skip already done
    if pid in done_ids:
        skip_count += 1
        continue

    # Skip if no input_output data
    if not problem.get("input_output"):
        print(f"[{i+1}/{len(problems)}] ⏭️  Skipped (no input_output): {title}")
        skip_count += 1
        continue

    difficulty = problem.get("difficulty", "?")
    print(f"[{i+1}/{len(problems)}] ⚙️  Enriching: {title} ({difficulty})...")

    try:
        resp = requests.post(API_URL, json=problem, timeout=TIMEOUT)

        if resp.status_code == 200:
            result = resp.json()

            # Start with only the clean filtered fields
            enriched_problem = filter_problem_fields(problem)

            # Add enriched fields from Qwen + parsed test cases
            enriched_problem["function_signature"] = result.get("function_signature", {})
            enriched_problem["public_testcases"]   = result.get("public_testcases", [])
            enriched_problem["hidden_testcases"]   = result.get("hidden_testcases", [])
            enriched_problem["starter_code_langs"] = result.get("starter_code", {})
            enriched_problem["pipeline"]           = result.get("pipeline", "dataset_driven")
            enriched_problem["test_case_source"]   = result.get("test_case_source", "leetcode_dataset")

            enriched.append(enriched_problem)
            done_ids.add(pid)
            success_count += 1

            # Save after every problem — crash-safe
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(enriched, f, indent=2, ensure_ascii=False)

            sig_name = result.get("function_signature", {}).get("name", "?")
            n_public = len(result.get("public_testcases", []))
            n_hidden = len(result.get("hidden_testcases", []))
            n_langs  = len(result.get("starter_code", {}))
            print(f"         ✅ fn={sig_name}, public={n_public}, hidden={n_hidden}, langs={n_langs}")

        else:
            fail_count += 1
            print(f"         ❌ HTTP {resp.status_code}: {resp.text[:200]}")

    except requests.exceptions.Timeout:
        fail_count += 1
        print(f"         ⏱️  Timeout after {TIMEOUT}s — skipping")

    except Exception as e:
        fail_count += 1
        print(f"         ❌ Error: {e}")

    if (i + 1) % 50 == 0:
        print(f"\n── Progress: {len(enriched)}/{len(problems)} done | "
              f"✅ {success_count} | ❌ {fail_count} | ⏭️ {skip_count} ──\n")

    time.sleep(DELAY_SECONDS)

print("\n" + "=" * 60)
print(f"✅ Enrichment complete!")
print(f"   Total enriched  : {len(enriched)}")
print(f"   Success         : {success_count}")
print(f"   Failed          : {fail_count}")
print(f"   Skipped         : {skip_count}")
print(f"   Output file     : {OUTPUT_FILE}")
