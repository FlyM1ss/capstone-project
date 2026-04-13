FROM nvidia/cuda:12.1.1-runtime-ubuntu22.04

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cu121

RUN pip install --no-cache-dir \
    sentence-transformers \
    fastapi \
    uvicorn

COPY embedding_server.py .

EXPOSE 8001

CMD ["uvicorn", "embedding_server:app", "--host", "0.0.0.0", "--port", "8001"]
