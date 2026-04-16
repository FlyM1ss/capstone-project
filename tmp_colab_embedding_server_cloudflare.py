"""Colab cell: Qwen3-Embedding-0.6B FastAPI server fronted by a Cloudflare quick tunnel.

Setup (one-time, separate cell):
  !pip install -q sentence-transformers fastapi uvicorn nest_asyncio
  !wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
  !chmod +x /usr/local/bin/cloudflared
"""

import asyncio
import json
import re
import socket
import subprocess
import threading
import time
import urllib.error
import urllib.request

import nest_asyncio
import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

# Colab kernel already owns an asyncio loop; nest_asyncio lets uvicorn coexist.
nest_asyncio.apply()

device = "cuda" if torch.cuda.is_available() else "cpu"
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
model.to(device)
print(f"Model loaded on {model.device}")

app = FastAPI()


class EmbedRequest(BaseModel):
    texts: list[str]


@app.post("/embed")
def embed(req: EmbedRequest):
    # Sync handler: Starlette dispatches it to its threadpool, so model.encode
    # (CPU/GPU-blocking) doesn't stall the asyncio loop for concurrent calls.
    embeddings = model.encode(req.texts, normalize_embeddings=True)
    return {"embeddings": embeddings.tolist()}


@app.get("/health")
def health():
    return {"status": "ok", "model": "Qwen3-Embedding-0.6B", "device": str(model.device)}


config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="warning")
server = uvicorn.Server(config)


def _serve():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(server.serve())


threading.Thread(target=_serve, daemon=True).start()

server_deadline = time.time() + 30
while not server.started and time.time() < server_deadline:
    time.sleep(0.1)
if not server.started:
    raise RuntimeError("uvicorn failed to start within 30s")

proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--no-autoupdate", "--url", "http://localhost:8001"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

URL_PATTERN = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")
public_url: str | None = None

tunnel_deadline = time.time() + 60
while time.time() < tunnel_deadline and public_url is None:
    line = proc.stdout.readline()
    if not line:
        if proc.poll() is not None:
            raise RuntimeError("cloudflared exited before publishing a URL")
        time.sleep(0.1)
        continue
    print(line, end="")
    match = URL_PATTERN.search(line)
    if match:
        public_url = match.group(0)

if public_url is None:
    raise RuntimeError("Did not see a trycloudflare.com URL within 60s")


def _drain():
    for _ in proc.stdout:
        pass


threading.Thread(target=_drain, daemon=True).start()

print("\nEmbedding server ready!")
print("Set this in your .env (single line, no quotes):")
print(f"EMBEDDING_API_URL={public_url}/embed\n")

# trycloudflare.com DNS can take a few seconds to propagate after the tunnel is published.
req = urllib.request.Request(
    f"{public_url}/embed",
    data=json.dumps({"texts": ["smoke test"]}).encode(),
    headers={"Content-Type": "application/json"},
)
last_err: Exception | None = None
for attempt in range(6):
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            dim = len(json.loads(resp.read())["embeddings"][0])
        print(f"Public smoke-test OK — embedding dim={dim}")
        break
    except (socket.gaierror, urllib.error.URLError) as e:
        last_err = e
        time.sleep(2 ** attempt)
else:
    raise RuntimeError(f"smoke test failed after retries: {last_err}")
