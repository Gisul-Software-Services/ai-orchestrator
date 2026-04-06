# syntax=docker/dockerfile:1.6
# Use a PyTorch CUDA runtime base so CI doesn't download massive torch+nvidia wheels.
# This drastically reduces disk usage on GitHub-hosted runners.
FROM pytorch/pytorch:2.10.0-cuda12.1-cudnn9-runtime

WORKDIR /app

ENV HF_HOME=/root/.cache/huggingface
ENV PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:128

ENV DEBIAN_FRONTEND=noninteractive

# System deps
RUN apt-get update --fix-missing \
  && apt-get install -y --no-install-recommends \
     curl \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Install pip + ML deps
RUN pip3 install --no-cache-dir --upgrade pip \
  && rm -rf /root/.cache/pip

COPY model-service/requirements.txt /app/requirements.txt
COPY model-service/requirements-gpu.txt /app/requirements-gpu.txt
# Install dependencies in ONE pass (avoids duplicate torch/vLLM downloads).
# Use BuildKit pip cache to reduce bandwidth + disk churn in CI.
RUN --mount=type=cache,target=/root/.cache/pip \
  pip3 install -r /app/requirements-gpu.txt \
  && rm -rf /root/.cache/pip

# Copy model-service entrypoint (required by spec)
COPY model-service/model_service_entrypoint.py /app/model_service_entrypoint.py

# Copy model app code.
COPY backend/model_app /app/model_app

# Copy assets (FAISS indexes + enriched DSA json, etc.)
COPY assets /app/assets

EXPOSE 7001
ENV MODEL_SERVICE_SELF_URL=http://127.0.0.1:7001
ENV ASSETS_DIR=/app/assets

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
  CMD curl --fail http://localhost:7001/docs || exit 1

CMD ["uvicorn", "model_service_entrypoint:app", "--host", "0.0.0.0", "--port", "7001"]

