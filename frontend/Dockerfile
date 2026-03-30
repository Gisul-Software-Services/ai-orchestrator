FROM python:3.11-slim

WORKDIR /app

# Install only what the frontend needs
RUN pip install --no-cache-dir \
    streamlit==1.36.0 \
    requests==2.32.3 \
    pandas==2.2.2 \
    plotly==5.18.0 \
    matplotlib==3.9.0

# Copy the frontend app
COPY frontend_app.py /app/frontend_app.py

# Expose Streamlit port
EXPOSE 8501

ENV API_BASE=http://localhost:9000/api/v1

CMD ["streamlit", "run", "frontend_app.py", \
     "--server.port=8501", \
     "--server.address=0.0.0.0", \
     "--server.headless=true"]