# Gisul model

Question-generation stack: **gateway** (FastAPI proxy, auth, billing) and **model service** (FastAPI + vLLM / GPU). This repo also includes a **Next.js** playground under `frontend/web`.

## Docker quickstart (pull + run)

### Linux + NVIDIA GPU (vLLM)

```bash
# Pull pinned images (recommended)
docker pull gisul/backend-api:<git-sha>
docker pull gisul/model-service:<git-sha>-gpu
docker pull gisul/model-frontend:<git-sha>

# Run
export IMAGE_TAG=<git-sha>
docker compose up -d
docker compose ps
```

### Mac (Apple Silicon) testing (Qwen via Ollama)

```bash
# On the Mac host (outside Docker)
ollama pull qwen2.5:7b-instruct

# Pull Mac model-service image
docker pull gisul/model-service:mac

# Run the stack using the Mac override
docker compose -f docker-compose.yml -f docker-compose.mac.yml up -d
docker compose ps
```

## Prerequisites

- **Python 3.11** (matches the gateway Docker image `python:3.11-slim` and is the version to standardize on locally). Python 3.12 may work for the GPU stack but is not what the gateway image pins.
- **Node.js 20+** (LTS) and **npm** for the frontend.
- **NVIDIA GPU + CUDA** if you run the full model locally (same dependency set as `model-service`). Gateway-only development does not require a GPU.

## Clone and Python environment

From the repository root:

```bash
cd gisul_model

# Use Python 3.11 explicitly so the venv matches production-ish images.
python3.11 --version   # expect 3.11.x

python3.11 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# Install / upgrade pip inside the venv (must be the venv’s python, not system pip).
python -m pip install --upgrade pip setuptools wheel

# Confirm interpreter and pip point at the same environment.
python --version
python -m pip --version
```

You should see `pip` coming from `.../venv/...` and a **pip version line** that references the same `python3.11` (or `python`) in that `venv`. If `pip install` affects a different Python, use `python -m pip install ...` instead of bare `pip install`.

## Dependency layout (one manifest per area)

| Area | Manifest | Purpose |
|------|-----------|--------|
| **Backend** (gateway API) | `backend/requirements.txt` | FastAPI proxy, Mongo, Redis, httpx, billing. Used by `backend/gateway/Dockerfile` (build context `backend/`). |
| **Model service** | `model-service/requirements.txt` | vLLM, torch+cu128, sentence-transformers, FAISS, etc. Same file is copied into the model Docker image. |
| **Frontend** (Next.js) | `frontend/web/package.json` (+ `package-lock.json`) | Node dependencies for the web app. Install with `npm ci` from `frontend/web`. |

Application code for the model lives under `backend/model_app/`; it does **not** have its own `requirements.txt` — use **`model-service/requirements.txt`** for that runtime.

## Install Python dependencies

Pick one path depending on what you run locally.

### Model service / full local model (GPU)

Use the pinned set (CUDA wheels via the PyTorch extra index in the file). Requires a CUDA-capable machine.

```bash
python -m pip install -r model-service/requirements.txt
```

### Gateway only (lightweight; proxies to a model service running elsewhere)

```bash
python -m pip install -r backend/requirements.txt
```

## Environment files

- **Gateway + local scripts:** copy `backend/.env.example` to `backend/.env` and fill in values (MongoDB, Redis, `MODEL_SERVICE_URL`, etc.).
- **Model service (Docker / GPU container):** copy `model-service/.env.example` to `model-service/.env` when using compose or a local GPU server that reads that file.

Never commit real `.env` files; they are listed in `.gitignore`.

## Run services locally (development)

Use the same activated `venv` and repo root as the working directory.

### Terminal 1 — Model service (GPU) on port 7001

```bash
cd /path/to/gisul_model
source venv/bin/activate
set -a && source backend/.env && set +a
PYTHONPATH=backend uvicorn model_app.main:app --host 0.0.0.0 --port 7001
```

### Terminal 2 — Gateway on port 7000

Point `MODEL_SERVICE_URL` in `backend/.env` at the model service (e.g. `http://127.0.0.1:7001`).

```bash
cd /path/to/gisul_model
source venv/bin/activate
set -a && source backend/.env && set +a
PYTHONPATH=. uvicorn backend.gateway.main:app --host 0.0.0.0 --port 7000
```

### Terminal 3 — Frontend on port 7002

```bash
cd frontend/web
npm ci
PORT=7002 npm run dev -- -p 7002
```

Open: [http://127.0.0.1:7002](http://127.0.0.1:7002)

## Docker

For containerized Redis, model-service, and gateway, see `docker-compose.yml` at the repo root.

### Images and tags (what to pull)

We publish multiple `gisul/model-service` variants because **vLLM/CUDA (GPU)** and **macOS dev (Ollama)** are different runtimes:

- **Linux + NVIDIA GPU (vLLM/CUDA)**:
  - `gisul/model-service:gpu`
  - `gisul/model-service:<git-sha>-gpu`
  - `gisul/model-service:latest` and `gisul/model-service:<git-sha>` also point at the **GPU** build
- **Mac dev (Apple Silicon) / Ollama backend**:
  - `gisul/model-service:mac`
  - `gisul/model-service:<git-sha>-mac`

Gateway and frontend are published as multi-arch images and should run on both Intel/AMD and Apple Silicon:

- `gisul/backend-api:latest` / `gisul/backend-api:<git-sha>`
- `gisul/model-frontend:latest` / `gisul/model-frontend:<git-sha>`

### Run on Linux with NVIDIA GPU (production-style)

This uses the **GPU** model-service image (vLLM) and requires NVIDIA Container Toolkit.

```bash
# Pull pinned images (recommended)
docker pull gisul/backend-api:<git-sha>
docker pull gisul/model-service:<git-sha>-gpu
docker pull gisul/model-frontend:<git-sha>

# Or use latest
# docker pull gisul/model-service:gpu

# Run the stack
export IMAGE_TAG=<git-sha>
docker compose up -d
docker compose ps
```

### Run on Mac (Apple Silicon) for testing (Qwen via Ollama)

On macOS, vLLM/NVML/CUDA won’t run. For local testing we run **Qwen via Ollama** on the Mac host and the repo’s model-service container calls it using env vars.

1) Start Ollama on the Mac and pull Qwen (example):

```bash
ollama pull qwen2.5:7b-instruct
```

2) Pull the **Mac** model-service image and start the stack with the Mac override:

```bash
docker pull gisul/model-service:mac

# Start using the Mac override (build/run config switches model-service to Dockerfile.mac)
docker compose -f docker-compose.yml -f docker-compose.mac.yml up -d
docker compose ps
```

3) Ensure `model-service/.env` contains (or export as environment variables):

- `LLM_BACKEND=ollama`
- `OLLAMA_BASE_URL=http://host.docker.internal:11434`
- `OLLAMA_MODEL=qwen2.5:7b-instruct`
