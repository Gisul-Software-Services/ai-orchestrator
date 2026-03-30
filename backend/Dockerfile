FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

WORKDIR /app

ENV CUDA_HOME=/usr/local/cuda
ENV LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH
ENV BNB_CUDA_VERSION=121
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update --fix-missing && apt-get install -y \
    python3 \
    python3-pip \
    git \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install --upgrade pip

COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# 🔥 ADD THIS LINE
RUN pip3 install faiss-cpu

COPY backend/qwen_model_server_script_multiple.py /app/qwen_model_server_script_multiple.py

COPY assets/dsa-coding/dsa_enriched.json /app/assets/dsa-coding/dsa_enriched.json
COPY assets/dsa-coding/dsa_faiss.index /app/assets/dsa-coding/dsa_faiss.index
COPY assets/dsa-coding/dsa_metadata.json /app/assets/dsa-coding/dsa_metadata.json

EXPOSE 9000

CMD ["uvicorn", "qwen_model_server_script_multiple:app", "--host", "0.0.0.0", "--port", "9000"]