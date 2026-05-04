# Gisul AI Orchestrator

An AI-powered assessment platform for technical competency evaluation. The platform generates questions, evaluates candidate submissions, and provides detailed AI feedback across multiple engineering domains.

---

## Architecture

The platform runs as 3 services + Redis:

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Frontend      │────▶│    Gateway      │────▶│  Model Service  │
│  Next.js :7002  │     │  FastAPI :7000  │     │  FastAPI :7001  │
│  Admin UI       │     │  Auth + Billing │     │  Qwen / vLLM    │
└─────────────────┘     └────────┬────────┘     └─────────────────┘
                                 │
                         ┌───────▼───────┐
                         │     Redis     │
                         │    :6379      │
                         │  Jobs + Cache │
                         └───────────────┘
```

| Service | Port | Purpose |
|---|---|---|
| `frontend` | 7002 | Next.js admin console |
| `backend-api` (gateway) | 7000 | Auth, billing, org verification, proxy |
| `model-service` | 7001 | Qwen/vLLM — generation + evaluation |
| `redis` | 6379 | Async job queue + response cache |

---

## Competencies

### Generation
| Competency | Endpoint |
|---|---|
| Topics | `POST /api/v1/generate-topics` |
| MCQ | `POST /api/v1/generate-mcq` |
| Subjective | `POST /api/v1/generate-subjective` |
| Coding | `POST /api/v1/generate-coding` |
| SQL | `POST /api/v1/generate-sql-question` |
| DSA | `POST /api/v1/generate-dsa-question` |
| DevOps | `POST /api/v1/generate-devops-question` |
| Cloud (AWS) | `POST /api/v1/generate-cloud-question` |
| AIML | `POST /api/v1/generate-aiml` |

### Evaluation
All evaluation endpoints have both sync and async variants. Use async (`/async`) to avoid timeouts.

| Competency | Async Endpoint |
|---|---|
| DSA | `POST /api/v1/evaluation/dsa/async` |
| AIML | `POST /api/v1/evaluation/aiml/async` |
| SQL | `POST /api/v1/evaluation/sql/async` |
| DevOps | `POST /api/v1/evaluation/devops/async` |
| Cloud | `POST /api/v1/evaluation/cloud/async` |
| Linux | `POST /api/v1/evaluation/linux/async` |
| Design | `POST /api/v1/evaluation/design/async` |
| Data Engineering | `POST /api/v1/evaluation/data-engineering/async` |

Poll async job results:
```
GET /api/v1/job/{job_id}
```

---

## Data Engineering Evaluation

The Data Engineering evaluator uses a 3-layer scoring pipeline:

```
Candidate submits PySpark code / written answer
        ↓
Layer 1: Deterministic Validation   (execution results from engine → DataFrame comparison)
Layer 2: Static Partial Credit      (PySpark pattern matching — only when execution fails)
Layer 3: AI Review                  (Qwen Coder — code quality, performance, best practices)
        ↓
Final score = deterministic overrides AI (with fallback exceptions)
```

**Request body:**
```json
{
  "question": {
    "id": "q-001",
    "title": "GroupBy Aggregation",
    "description": "Compute total sales per region",
    "question_type": "coding",
    "difficulty": "medium",
    "rubric_items": ["use groupBy", "aggregate sum"],
    "test_cases": [
      {
        "input_data": { "rows": [{"region": "North", "amount": 100}] },
        "expected_output": [{"region": "North", "total": 100}]
      }
    ]
  },
  "submission": {
    "code": "...",
    "answer": "",
    "execution_results": [
      {
        "test_case_index": 0,
        "status": "success",
        "output_df": [{"region": "North", "total": 100}],
        "error_message": null
      }
    ]
  },
  "use_cache": true
}
```

**Response:**
```json
{
  "final_score": 100.0,
  "deterministic_score": 100.0,
  "static_partial_score": 0.0,
  "ai_score": 85.0,
  "score_reason": "exact_match",
  "is_correct": true,
  "per_test_case_results": [...],
  "ai_feedback": {
    "overall_score": 85.0,
    "correctness_feedback": "...",
    "performance_feedback": "...",
    "best_practices_feedback": "...",
    "improvement_suggestions": [...],
    "strengths": [...],
    "areas_for_improvement": [...]
  }
}
```

---

## Project Structure

```
gisul_model/
├── backend/
│   ├── gateway/              # FastAPI gateway (auth, billing, proxy)
│   │   ├── Dockerfile
│   │   └── main.py
│   └── model_app/
│       ├── api/routes/       # All API route handlers
│       ├── competencies/     # Per-competency schemas + generators
│       │   ├── aiml/
│       │   ├── cloud/
│       │   ├── data_engineering/
│       │   ├── design/
│       │   ├── devops/
│       │   ├── dsa/
│       │   └── sql/
│       ├── evaluation/       # Evaluator modules (one per competency)
│       └── services/         # Shared: cache, jobs, model, RAG
├── model-service/
│   ├── Dockerfile            # GPU (vLLM + CUDA)
│   ├── Dockerfile.mac        # Mac (Ollama)
│   └── requirements.txt
├── frontend/
│   └── web/                  # Next.js admin console
│       └── Dockerfile
├── assets/                   # FAISS indexes, DSA enriched data
├── docker-compose.yml        # Production (Linux + GPU)
├── docker-compose.mac.yml    # Mac override (Ollama)
└── README.md
```

---

## Quick Start

### Prerequisites
- Docker + Docker Compose
- NVIDIA GPU + CUDA (for model-service)
- NVIDIA Container Toolkit

### 1. Clone and configure

```bash
git clone https://github.com/Gisul-Software-Services/ai-orchestrator.git
cd ai-orchestrator
```

Copy and fill in the env files:

```bash
cp backend/.env.example backend/.env
cp model-service/.env.example model-service/.env
cp frontend/web/.env.example frontend/web/.env.local
```

Key values to set:

**`backend/.env`**
```
MONGODB_URI=mongodb+srv://...
ADMIN_API_KEY=your-admin-key
REDIS_URL=redis://redis:6379
MODEL_SERVICE_URL=http://model-service:7001
```

**`model-service/.env`**
```
MONGODB_URI=mongodb+srv://...
REDIS_URL=redis://redis:6379
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct-AWQ
```

**`frontend/web/.env.local`**
```
ADMIN_TOKEN=your-admin-token
ADMIN_SESSION_SECRET=your-session-secret
ADMIN_API_KEY=your-admin-key
GATEWAY_BASE_URL=http://backend-api:7000
```

### 2. Build and run

```bash
docker compose up -d --build
docker compose ps
```

### 3. Verify

```bash
# Gateway health
curl http://localhost:7000/api/v1/health

# Frontend
open http://localhost:7002
```

---

## Mac (Apple Silicon) — Local Dev

Requires [Ollama](https://ollama.com) running on the host:

```bash
ollama pull qwen2.5:7b-instruct

docker compose -f docker-compose.yml -f docker-compose.mac.yml up -d
```

Set in `model-service/.env`:
```
LLM_BACKEND=ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:7b-instruct
```

---

## Local Development (without Docker)

Requires Python 3.11 and Node 20+.

```bash
# Create venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r model-service/requirements.txt

# Terminal 1 — Model service (port 7001)
uvicorn model_service_entrypoint:app --host 0.0.0.0 --port 7001

# Terminal 2 — Gateway (port 7000)
uvicorn backend.gateway.main:app --host 0.0.0.0 --port 7000

# Terminal 3 — Frontend (port 7002)
cd frontend/web
npm ci
npm run dev -- -p 7002
```

---

## Authentication

All API calls require one of:

- **Admin key** — `X-Api-Key: <ADMIN_API_KEY>` — bypasses org verification, full access
- **Org API key** — `X-Api-Key: <org-key>` — validated against MongoDB `api_keys` collection, subject to rate limiting (20 req/min per org)

---

## Testing

```bash
# Test all evaluation endpoints
python3 test_all_evaluations.py

# Test data engineering endpoint specifically
python3 test_de_endpoint.py

# Test deterministic scoring logic (no server needed)
python3 test_de_eval_logic.py
```

---

## Dependencies

| Area | Manifest |
|---|---|
| Gateway | `backend/requirements.txt` |
| Model service | `model-service/requirements.txt` |
| Frontend | `frontend/web/package.json` |
