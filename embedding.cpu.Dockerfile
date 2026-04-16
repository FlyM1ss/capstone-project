FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    "transformers>=4.51.0" \
    sentence-transformers \
    fastapi \
    uvicorn

COPY embedding_server.py .

EXPOSE 8001

CMD ["uvicorn", "embedding_server:app", "--host", "0.0.0.0", "--port", "8001"]
