FROM python:3.11-slim
WORKDIR /app
# Build context must be the `backend/` directory (see docker-compose / CI).
# Package imports use ``backend.gateway.*`` → need ``backend/gateway`` on PYTHONPATH.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN mkdir -p /app/backend
COPY gateway /app/backend/gateway
ENV PYTHONPATH=/app
EXPOSE 7000
CMD ["uvicorn", "backend.gateway.main:app", "--host", "0.0.0.0", "--port", "7000"]
