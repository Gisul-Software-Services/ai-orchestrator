FROM python:3.10-slim

WORKDIR /app

# Install dependencies first (for better layer caching).
COPY backend/api_gateway/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -U pip \
  && pip install --no-cache-dir -r /app/requirements.txt \
  && rm -rf /root/.cache/pip

# Copy source code after dependencies are installed.
COPY backend/api_gateway/main.py /app/main.py

EXPOSE 7000

ENV MODEL_SERVICE_URL=http://model-service:7001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7000"]

