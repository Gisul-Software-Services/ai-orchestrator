FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04
WORKDIR /app
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update --fix-missing \
  && apt-get install -y --no-install-recommends python3 python3-pip curl \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /app/requirements.txt
RUN pip3 install --no-cache-dir -r /app/requirements.txt
COPY . /app/model_app
COPY ../../assets /app/assets
EXPOSE 7001
CMD ["uvicorn", "model_app.main:app", "--host", "0.0.0.0", "--port", "7001"]
