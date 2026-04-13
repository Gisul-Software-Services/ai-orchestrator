# Build from the repository root:
#   docker build -f backend/Dockerfile .
FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

WORKDIR /app

ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV BNB_CUDA_VERSION=121
ENV DEBIAN_FRONTEND=noninteractive
ENV ASSETS_DIR=/app/assets

RUN apt-get update --fix-missing && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

COPY backend/requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt

COPY backend /app/backend
COPY assets /app/assets

EXPOSE 9000

CMD ["uvicorn", "backend.model_app.main:app", "--host", "0.0.0.0", "--port", "9000"]
