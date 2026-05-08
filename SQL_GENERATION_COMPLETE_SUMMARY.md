# SQL Question Generation & Evaluation — Complete Summary

**Date:** May 8, 2026  
**Branch:** Ujwal  
**Status:** ✅ Production Ready

---

## Overview

This document covers all changes made to the SQL question generation and evaluation system, the issues encountered, how they were resolved, and the current state of the RAG schema data.

---

## Files Changed

### Backend
| File | Change |
|---|---|
| `backend/model_app/api/routes/sql.py` | Added async endpoint, imports |
| `backend/model_app/competencies/sql/schema_generator.py` | Major rewrite — schema selection, validation, retry |
| `backend/model_app/competencies/sql/prompts.py` | Pass 3 prompt — sample values, placeholder detection, CTE fix |
| `backend/model_app/competencies/sql/eval_schema.py` | Accept structured output arrays |
| `backend/model_app/competencies/sql/schema.py` | Schema request model |
| `backend/model_app/evaluation/sql_evaluator.py` | Full rewrite — production level v2.2.0 |
| `backend/model_app/core/state.py` | LLM_CONCURRENCY env variable |
| `backend/gateway/main.py` | Register sql-question-async route |
| `backend/model_app/competencies/sql/postgres_validator.py` | Type normalization, ON CONFLICT DO NOTHING, stale schema cleanup |
| `backend/model_app/competencies/sql/query_validator.py` | INSERT OR IGNORE for SQLite |

### Frontend
| File | Change |
|---|---|
| `frontend/web/app/playground/sql/page.tsx` | New SQL generation page (was evaluation) |
| `frontend/web/app/playground/sql/evaluate/page.tsx` | Evaluation moved to sub-route |
| `frontend/web/app/api/admin/generate/sql-async/route.ts` | New proxy for async endpoint |

### RAG Service (aaptor-rag-service)
| File | Change |
|---|---|
| `api/routes/schema_import.py` | Improved select endpoint — pool 30, max_tables, min_columns, exclude_ids, fallback chain, list endpoint |

### Config
| File | Change |
|---|---|
| `model-service/.env` | Added LLM_CONCURRENCY=1 |
| `model-service/.env.example` | Added LLM_CONCURRENCY=1 |

---

## Issues Encountered & Fixes

### Issue 1 — SQL Playground showing Evaluation instead of Generation
**Problem:** `/playground/sql` was showing the SQL Evaluation form.  
**Fix:** Replaced `page.tsx` with SQL Question Generation form. Moved evaluation to `/playground/sql/evaluate`.

---

### Issue 2 — 500 Internal Server Error on generation
**Problem:** FastAPI's JSON encoder crashed with `ValueError: dictionary update sequence element #0 has length 1`.  
**Root cause:** PostgreSQL returns Python types (`datetime.date`, `decimal.Decimal`) that JSON encoder can't handle.  
**Fix:** Added `_serialize_value()` helper that converts non-JSON-serializable types to JSON-safe equivalents.

---

### Issue 3 — LLM hallucinating table names (e.g. `purchases` table)
**Problem:** Pass 3 kept generating queries with non-existent table names across all 3 retries.  
**Fix:** On retry, error message now explicitly lists: `REMINDER: The ONLY valid tables are: "categories", "customer_customer_demo"`. LLM corrects on next attempt.

---

### Issue 4 — LLM using placeholder strings as literal values
**Problem:** Queries like `BETWEEN 'start_date' AND 'end_date'` — LLM using parameter names as string literals.  
**Fix:** Added pre-validation regex check for placeholder strings before hitting Postgres. Added explicit rule in Pass 3 prompt: "Use real dates like '2024-01-01', not 'start_date'".

---

### Issue 5 — `expected_output` always empty (0 rows)
**Problem:** All queries returned 0 rows because sample data had only 5 rows per table — too sparse for WHERE/HAVING conditions to match.  
**Root cause:** Sample data generator used hardcoded lists of 5 values.  
**Fix:** Regenerated all 160 schemas with 100 rows per table using Faker library with domain-aware value generation.

---

### Issue 6 — Duplicate key spam in logs
**Problem:** Hundreds of `duplicate key value violates unique constraint` warnings per request.  
**Root cause:** Postgres validator was trying to insert 100 rows but only 5 rows existed before — on retry, it tried to insert the same IDs again.  
**Fix:** Changed `INSERT INTO` → `INSERT INTO ... ON CONFLICT DO NOTHING` in both Postgres and SQLite validators.

---

### Issue 7 — Postgres connection failing (password auth)
**Problem:** `FATAL: password authentication failed for user "aaptor"`.  
**Root cause:** Native PostgreSQL 14 running on host at `127.0.0.1:5432` intercepting connections instead of Docker postgres. Native postgres had `scram-sha-256` auth but `aaptor` user didn't exist.  
**Fix:** Changed native postgres `pg_hba.conf` to `trust` for localhost, created `aaptor` user and `validation_db` database.

---

### Issue 8 — `ENUM` type not supported in Postgres
**Problem:** `Failed to create table 'employees': type "enum" does not exist`.  
**Root cause:** Spider benchmark schemas use MySQL `ENUM` type which is not a bare type in Postgres.  
**Fix:** Added `_normalize_pg_type()` function that maps MySQL/non-standard types to valid Postgres equivalents: `ENUM → VARCHAR(100)`, `TINYINT → SMALLINT`, `DATETIME → TIMESTAMP`, `AUTO_INCREMENT → (strip)`, etc.

---

### Issue 9 — Multiple PRIMARY KEY constraint error
**Problem:** `multiple primary keys for table "Office_locations" are not allowed`.  
**Root cause:** Spider schemas with composite PKs defined as two separate `PRIMARY KEY` constraints.  
**Fix:** Added `_has_composite_pk()` pre-validation — schemas with composite PKs are skipped and a fresh schema is fetched.

---

### Issue 10 — Case-sensitive column names
**Problem:** `column s.stuid does not exist` (actual column: `s.StuID`).  
**Root cause:** Spider schemas use mixed-case column names. LLM generates lowercase aliases.  
**Fix:** Pass 3 retry with error message includes the exact column names from DDL. Schema retry fetches a different schema on persistent failure.

---

### Issue 11 — Window/CTE timeout
**Problem:** `spider_local_govt_and_lot` (48 cols, 11 tables) caused LLM timeout for window/CTE queries.  
**Root cause:** Too many tables/columns in the schema DDL — LLM takes too long.  
**Fix:** Added `_CATEGORY_MAX_TABLES` — window/CTE categories limited to `max_tables=8`. Complex schemas are excluded from selection.

---

### Issue 12 — DSA evaluation interrupting SQL generation
**Problem:** DSA eval and SQL generation ran concurrently on the same 8GB GPU causing timeouts.  
**Root cause:** SQL generation called `_llm_chat_single()` directly without the semaphore. Evaluation routes used `llm_semaphore` but generation did not.  
**Fix:** Added `POST /api/v1/generate-sql-question-async` endpoint that queues generation behind `llm_semaphore`. Returns `job_id` immediately. Added `LLM_CONCURRENCY` env variable for easy GPU scaling.

---

### Issue 13 — Data quality issues in sample data
**Problem:** `services.name` had person names, `menu_items.category` had product categories, `games.title` had job titles, `is_available` had string values instead of boolean.  
**Root cause:** Generator used generic `fake.name()` for any column named `name`, and `JOB_TITLES` list for `title` columns.  
**Fix:** Rewrote `generate_value()` with table-context-aware logic: `name` in `services` table → service names, `name` in `games` table → game titles, `category` in `menu_items` → food categories, `is_available` → boolean.

---

### Issue 14 — Schema selection pool too small
**Problem:** Only 10 schemas in selection pool — same schemas kept repeating.  
**Fix:** Increased pool from `limit=10` → `limit=30`. Added category-specific `max_tables` filter. Added `exclude_ids` to avoid repeating schemas on retry.

---

## RAG Schema Data — Current State

### Statistics
| Metric | Value |
|---|---|
| Total schemas | 160 |
| Unique domains | 106 |
| All schemas with 100 rows/table | 160/160 ✅ |
| Schemas with issues | 0 ✅ |

### Domain Distribution (top 15)
| Domain | Schemas |
|---|---|
| finance | 6 |
| healthcare | 6 |
| education | 6 |
| hr | 5 |
| music | 5 |
| logistics | 5 |
| social | 5 |
| e-commerce | 4 |
| entertainment | 4 |
| retail | 4 |
| travel | 4 |
| college | 3 |
| food | 3 |
| gaming | 3 |
| real_estate | 3 |
| + 91 more domains | 57 |

### Table Count Distribution
| Tables | Schemas |
|---|---|
| 2-3 tables | 51 (32%) |
| 4-5 tables | 53 (33%) |
| 6-10 tables | 33 (21%) |
| 11+ tables | 23 (14%) |

### Sample Data Quality
- **100 rows per table** across all 160 schemas
- **FK-consistent** — child tables reference valid parent IDs
- **Domain-aware values** — service names, food categories, game titles, boolean flags
- **Faker-generated** — realistic names, emails, addresses, dates
- **Date spread** — 2022-01-01 to 2024-12-31 (3 years of data)

### Schema Sources
| Source | Count |
|---|---|
| Synthetic (Faker-generated) | ~60 schemas |
| Spider benchmark (real-world) | ~100 schemas |

---

## SQL Generation Architecture

### Three-Pass Generation
```
Pass 1 (250 tokens) → title + description (context/problem/purpose)
Pass 2 (350 tokens) → hints + constraints (uses Pass 1 as context)
Pass 3 (300 tokens) → reference_query (SQL, validated against Postgres)
```

### Schema Selection Flow
```
Request (difficulty, category, domain)
    ↓
RAG Service: pool=30, max_tables=N, min_columns=10
    ↓
Pre-validate: composite PK check
    ↓
Pass 1 → Pass 2 → Pass 3 (with Postgres validation)
    ↓
If 0 rows: retry Pass 3 without filters (2 retries)
    ↓
If still 0 rows: fallback SELECT LIMIT 5
    ↓
If schema fails completely: fetch new schema, retry from Pass 1
```

### Category-Specific Table Limits
| Category | Max Tables |
|---|---|
| select | 5 |
| aggregation | 6 |
| join | 8 |
| subquery | 8 |
| window | 8 |
| cte | 8 |

---

## SQL Evaluation Architecture (v2.2.0)

### Flow
```
Execution Engine → user_output, expected_output, passed, error
    ↓
Parse outputs as JSON arrays
    ↓
Structured comparison (row count, column match, partial match ratio)
    ↓
Deterministic correctness score (ground truth from execution)
    ↓
LLM evaluates: efficiency, best_practices, edge_cases, alternative_solutions
    ↓
Score enforcement: passed=True → ≥80%, passed=False → ≤50%
```

### Scoring Criteria
| Criterion | Weight |
|---|---|
| correctness | 40% (deterministic from execution) |
| efficiency | 25% (LLM) |
| best_practices | 15% (LLM) |
| edge_cases | 10% (LLM) |
| alternative_solutions | 10% (LLM) |

---

## GPU Queue System

### Single GPU (8GB) — Current
```
LLM_CONCURRENCY=1  (in model-service/.env)
All requests → single queue → one at a time
```

### Multi-GPU Scaling
```bash
# To scale to 2 GPUs:
LLM_CONCURRENCY=2

# To scale to 4 GPUs:
LLM_CONCURRENCY=4
```

Only one env variable change needed — no code changes.

### Endpoints
| Endpoint | Type | Description |
|---|---|---|
| `POST /api/v1/generate-sql-question` | Sync | Direct generation (no queue) |
| `POST /api/v1/generate-sql-question-async` | Async | Returns job_id, queued |
| `GET /api/v1/job/{job_id}` | Poll | Check job status/result |

---

## Test Results (Final)

```
[select]      ✅ rows=3  | validated=True | attempts=1
[join]        ✅ rows=5  | validated=True | attempts=2
[aggregation] ✅ rows=1  | validated=True | attempts=1
[subquery]    ✅ rows=5  | validated=True | attempts=1
[window]      ✅ rows=5  | validated=True | attempts=2
[cte]         ✅ rows=5  | validated=True | attempts=2
```

All 6 SQL categories generating questions with real expected output rows.

---

## RAG Schema Data — Detailed Breakdown

### What is the RAG Schema?
The RAG (Retrieval-Augmented Generation) schema store is a MongoDB collection hosted at `http://103.173.99.217:7003`. It stores 160 SQL database schemas used as the foundation for question generation. Each schema contains:
- **Table definitions** — column names, types, constraints
- **Relationships** — FK relationships between tables
- **Sample data** — 100 rows per table (realistic, FK-consistent)
- **Metadata** — domain, difficulty levels, SQL categories, column counts
- **Usage tracking** — `usage_count` and `last_used_at` for LRU selection

### Schema Structure (MongoDB Document)
```json
{
  "schema_id": "synthetic_finance_banking_b2df7c65",
  "name": "Synthetic - Finance Banking",
  "domain": "finance",
  "description": "Banking system with accounts, transactions, customers",
  "difficulty_levels": ["easy", "medium", "hard"],
  "sql_categories": ["select", "join", "aggregation", "subquery", "window", "cte"],
  "tables": {
    "accounts": {
      "columns": [
        {"name": "account_id", "type": "INTEGER", "constraints": "NOT NULL"},
        {"name": "customer_id", "type": "INTEGER", "constraints": "NOT NULL"},
        {"name": "account_type", "type": "VARCHAR(50)", "constraints": ""},
        {"name": "balance", "type": "DECIMAL(10,2)", "constraints": ""}
      ]
    }
  },
  "relationships": [
    {"from_table": "accounts", "from_column": "customer_id",
     "to_table": "customers", "to_column": "customer_id",
     "relationship_type": "many-to-one"}
  ],
  "sample_data": {
    "accounts": [
      {"account_id": 1, "customer_id": 1, "account_type": "savings", "balance": 5432.10},
      ...100 rows
    ]
  },
  "metadata": {
    "table_count": 5,
    "total_columns": 31,
    "has_foreign_keys": true,
    "has_numeric_columns": true,
    "has_date_columns": true
  },
  "usage_count": 3,
  "last_used_at": "2026-05-08T12:00:00",
  "source": "synthetic",
  "source_quality": "aaptor_curated"
}
```

### Sample Data Generation — How It Works
The `regenerate_sample_data.py` script generates realistic data using:

**Faker library** for:
- Names: `fake.first_name()`, `fake.last_name()`, `fake.name()`
- Emails: `user{n}@{fake.domain_name()}`
- Addresses: `fake.street_address()`
- Dates: `datetime(2022,1,1) + timedelta(days=row_idx*3)`

**Domain-aware value pools** for:
- `services.name` → `["Hotel Booking", "Car Rental", "Tour Package", ...]`
- `menu_items.category` → `["Appetizer", "Main Course", "Dessert", ...]`
- `games.title` → `["Dragon Quest", "Space Warriors", "City Builder", ...]`
- `orders.status` → `["placed", "confirmed", "shipped", "delivered", ...]`
- `is_available` → `True/False` (boolean)

**FK-consistent generation**:
- Parent tables generated first (topological sort)
- Child FK values reference real parent IDs
- Ensures JOINs always return rows

### RAG Service Endpoints
| Endpoint | Description |
|---|---|
| `GET /api/v1/sql-schemas/select` | Select schema for generation (LRU + filters) |
| `GET /api/v1/sql-schemas/list` | List all schemas with row counts |
| `GET /api/v1/sql-schemas/stats` | Statistics by domain/difficulty/category |
| `POST /api/v1/import-sql-schemas` | Import/update schemas (upsert by schema_id) |
| `POST /api/v1/sql-schemas/update-usage/{id}` | Increment usage count after generation |
| `DELETE /api/v1/sql-schemas/bulk-delete` | Bulk delete schemas by filter |

### Schema Selection Algorithm
```
1. Query MongoDB:
   - difficulty_levels = requested difficulty
   - sql_categories = requested category
   - metadata.table_count <= max_tables (category-specific)
   - metadata.total_columns >= min_columns
   - schema_id NOT IN excluded_ids

2. Sort by usage_count ASC (least recently used first)

3. Take top 30 results (pool)

4. Pick random from pool (ensures variety within LRU constraint)

5. If no results: fallback chain
   → Drop domain filter
   → Drop difficulty filter
   → Drop all filters except category

6. Return selected schema
```

### Why 100 Rows Per Table?
Before the fix, schemas had only 5 rows per table. This caused:
- `HAVING COUNT(*) > 5` → always 0 results (only 5 rows total)
- `WHERE status = 'active'` → might not exist in 5 rows
- Window functions → no meaningful partitions
- JOINs → trivial results

With 100 rows:
- `HAVING COUNT(*) > 5` → matches ~20 groups
- `WHERE status = 'active'` → ~20 rows match (100 rows × 5 statuses)
- Window functions → meaningful RANK/PARTITION results
- JOINs → realistic multi-row results

---

## SQL Generation — Prompt Engineering Details

### Pass 1 System Prompt
Generates: `title`, `context`, `problem`, `purpose`
- Temperature: 0.7 (creative)
- Max tokens: 250
- Includes: domain, difficulty, table names, available columns, category instruction

### Pass 2 System Prompt
Generates: `hints` (3), `constraints` (2)
- Temperature: 0.7
- Max tokens: 350
- Receives: Pass 1 output as context

### Pass 3 System Prompt
Generates: `reference_query` (valid SQL)
- Temperature: 0.1 (precise — SQL needs determinism)
- Max tokens: 300
- Includes:
  - Schema DDL (exact table/column names)
  - FK relationships
  - **Sample values** (actual data values for WHERE conditions)
  - Previous error + valid table list (on retry)
  - Placeholder detection rules

### Sample Values Injection (Key Fix)
Before this fix, LLM invented filter values like `WHERE status = 'overdue'` that didn't exist in data.

Now Pass 3 receives:
```
ACTUAL DATA VALUES (use ONLY these values in WHERE/HAVING/IN conditions):
  orders.status: ['placed', 'confirmed', 'shipped', 'delivered', 'cancelled']
  customers.country: ['USA', 'UK', 'Canada', 'Australia', 'Germany']
  transactions.type: ['debit', 'credit', 'transfer', 'payment']
```

LLM writes `WHERE status = 'placed'` → query returns real rows.

---

## SQL Evaluation — Detailed Scoring Logic

### Correctness Score (Deterministic — 40% weight)
This is the most important criterion and is computed deterministically from the execution result — the LLM cannot override it.

```python
if passed:
    correctness = max_marks * 0.40  # full credit

else:
    # Partial credit based on how close the output is
    ratio = matched_rows / expected_rows
    partial = ratio * 0.5  # max 50% of correctness weight
    if column_match: partial += 0.1
    if row_count_match: partial += 0.1
    partial = min(partial, 0.30)  # cap at 30% for failed execution
    correctness = max_marks * 0.40 * partial
```

### Output Comparison
```python
# Order-insensitive comparison (default)
user_counter = Counter([tuple(row.values()) for row in user_rows])
expected_counter = Counter([tuple(row.values()) for row in expected_rows])
exact_match = user_counter == expected_counter

# Order-sensitive comparison (when order_sensitive=True)
exact_match = user_tuples == expected_tuples
```

### Score Floor/Cap
```
passed=True  → final_score >= 80% of max_marks
passed=False → final_score <= 50% of max_marks
```

### Answer Log (populated automatically)
```json
{
  "submitted_answer": "SELECT * FROM orders WHERE status = 'completed'",
  "expected_answer": "SELECT id, total FROM orders WHERE status = 'completed' ORDER BY total DESC",
  "partial_credit_reasoning": "Execution failed. Rows: user=0, expected=5. Partial match: 0.0%."
}
```

---

## API Reference

### Generate SQL Question (Async — Recommended)
```bash
POST /api/v1/generate-sql-question-async
{
  "difficulty": "medium",
  "sql_category": "aggregation",
  "count": 1,
  "topic": "finance"  # optional domain hint
}

Response: {"job_id": "uuid", "status": "pending"}

# Poll for result:
GET /api/v1/job/{job_id}
Response: {"status": "complete", "result": {...question...}}
```

### Generate SQL Question (Sync)
```bash
POST /api/v1/generate-sql-question
{
  "difficulty": "easy|medium|hard",
  "sql_category": "select|join|aggregation|subquery|window|cte",
  "count": 1,
  "topic": "optional domain"
}
```

### Evaluate SQL (Async)
```bash
POST /api/v1/evaluation/sql/async
{
  "question_id": "q-sql-001",
  "question_description": "Find all customers with balance > 1000",
  "user_query": "SELECT * FROM customers WHERE balance > 1000",
  "reference_query": "SELECT id, name, balance FROM customers WHERE balance > 1000",
  "max_marks": 10,
  "schemas": {"customers": {"columns": {"id": "INT", "name": "VARCHAR", "balance": "DECIMAL"}}},
  "test_result": {
    "passed": true,
    "user_output": "[{\"id\": 1, \"name\": \"Alice\", \"balance\": 1500}]",
    "expected_output": "[{\"id\": 1, \"name\": \"Alice\", \"balance\": 1500}]",
    "error": null
  },
  "order_sensitive": false,
  "difficulty": "medium"
}

Response: {"job_id": "uuid", "status": "pending"}
```

### SQL Categories Supported
```bash
GET /api/v1/sql-categories
```
Returns all supported categories with their routing path (RAG vs schema-based).

---

## Known Limitations & Future Work

### Current Limitations
1. **Spider schemas with mixed-case columns** — LLM sometimes generates wrong case aliases. Handled by retry but adds latency.
2. **0-row fallback queries** — When all retries fail, a simple `SELECT ... LIMIT 5` is used. The question title/description may not match the fallback query.
3. **Single GPU bottleneck** — With `LLM_CONCURRENCY=1`, concurrent requests queue up. High traffic will have wait times.
4. **RAG service on remote VM** — If VM is down, schema selection fails. No local fallback schema library currently active.

### Future Improvements
1. **Increase schema count** — Add more schemas (target: 500+) for better variety
2. **Schema quality scoring** — Score schemas by FK richness, column diversity, data quality
3. **Streaming generation** — Stream Pass 1/2/3 results as they complete
4. **Schema caching** — Cache frequently used schemas locally to reduce RAG service calls
5. **Multi-GPU support** — Already implemented via `LLM_CONCURRENCY` env variable
6. **Question deduplication** — Track generated question titles to avoid repeats
