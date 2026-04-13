FROM python:3.11-slim
WORKDIR /app
COPY backend/gateway/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY backend /app/backend
EXPOSE 7000
CMD ["uvicorn", "backend.gateway.main:app", "--host", "0.0.0.0", "--port", "7000"]
CMD ["uvicorn", "backend.gateway.main:app", "--host", "0.0.0.0", "--port", "7000"]
