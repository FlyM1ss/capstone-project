"""Local embedding server using Qwen3-Embedding-0.6B (auto-detects GPU/CPU)."""
import signal
import sys
from contextlib import asynccontextmanager

import torch
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Loading Qwen3-Embedding-0.6B on {device.upper()}...")
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
model.to(device)
print(f"Model loaded on {device.upper()} — ready to serve embeddings")


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    print("\nShutting down embedding server...")
    del model
    if device == "cuda":
        torch.cuda.empty_cache()
        print("GPU memory released.")
    print("Embedding server stopped.")


app = FastAPI(lifespan=lifespan)


class EmbedRequest(BaseModel):
    texts: list[str]


@app.post("/embed")
async def embed(req: EmbedRequest):
    embeddings = model.encode(req.texts, normalize_embeddings=True, show_progress_bar=False)
    return {"embeddings": embeddings.tolist()}


@app.get("/health")
async def health():
    return {"status": "ok", "model": "Qwen3-Embedding-0.6B", "device": device}


def _handle_shutdown(signum, frame):
    sig_name = signal.Signals(signum).name
    print(f"\n{sig_name} received — shutting down gracefully...")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, _handle_shutdown)
    signal.signal(signal.SIGTERM, _handle_shutdown)
    uvicorn.run(app, host="0.0.0.0", port=8001)
