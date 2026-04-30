# Cloud-Hosted Embedding Setup Guide

Run the **Qwen3-Embedding-0.6B** model on **Google Colab** (or similar cloud GPU providers) without needing a local NVIDIA GPU.

---

## Overview

This guide demonstrates how to:

1. Host the embedding server on Google Colab with free GPU access
2. Expose it publicly via Cloudflare quick tunnel (no configuration required)
3. Connect your local Docker stack to the cloud embedding service

**Key Benefits:**
- No local GPU required
- Free GPU compute (Google Colab)
- Public HTTPS URL with automatic tunneling
- Seamless integration with local Docker stack

---

## Prerequisites

- **Google Account** (for Colab)
- **Project running locally** (see [README.md](../README.md))
- **.env file** configured (see below)

---

## Step 1: Open Google Colab

1. Go to [colab.research.google.com](https://colab.research.google.com)
2. Sign in with your Google Account
3. Create a **New Notebook** or upload the code below

---

## Step 2: Install Dependencies

Run this cell **once** per Colab session:

```python
!pip install -q sentence-transformers fastapi uvicorn nest_asyncio
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared
```

**Expected output:** Installation completes silently (no errors = success)

---

## Step 3: Deploy the Embedding Server

Copy and run this cell in Colab:

```python
"""Colab cell: Qwen3-Embedding-0.6B FastAPI server fronted by a Cloudflare quick tunnel.

Setup (one-time, the cell above does this):
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
```

**Expected output:**
```
Model loaded on cuda
...
[cloudflared output]
...
Embedding server ready!
Set this in your .env (single line, no quotes):
EMBEDDING_API_URL=https://abc123def456-ghi.trycloudflare.com/embed

Public smoke-test OK — embedding dim=1024
```

**Copy the `EMBEDDING_API_URL=...` line for the next step.**

---

## Step 4: Configure Your Local .env

1. Stop your local Docker stack:
   ```bash
   docker compose down
   ```

2. Edit your `.env` file and update:
   ```env
   # Replace the local URL with the Colab URL from Step 3
   EMBEDDING_API_URL=https://abc123def456-ghi.trycloudflare.com/embed
   ```

3. **Do NOT use the local embedding service** — start with the external-embedding compose file:

   ```bash
   docker compose -f docker-compose.yml -f docker-compose.external-embedding.yml up -d
   ```

4. Verify the backend can reach the embedding service:
   ```bash
   docker compose logs backend | grep -i embed
   ```

   **Success**: You'll see embedding requests completing without errors.

---

## Step 5: Ingest Documents

Once services are running:

```bash
docker compose exec backend python -m app.scripts.ingest_all
```

Monitor progress:

```bash
docker compose logs -f backend
```

---

## Step 6: Test End-to-End

1. Open **http://localhost:3000** in your browser
2. Perform a search — results should appear
3. Upload a test document and search for its contents

---

## Keeping the Tunnel Active

The Colab notebook will keep the tunnel open as long as the cell is running. To keep it running long-term:

1. **Option A**: Set a timer to re-run the cell every 24 hours (Colab idle timeout)
2. **Option B**: Use a [hosted embedding service](#-alternative-hosting-providers) instead of Colab

---

## Colab Limitations and Workarounds

| Limitation | Impact | Workaround |
|-----------|--------|-----------|
| **24-hour runtime limit** | Tunnel goes down after 24h | Re-run cell, use auto-restart script |
| **Idle timeout** (30 min) | Colab closes if inactive | Keep a tab open or use Colab pro |
| **Shared GPU** | May be slow during peak hours | Use during off-peak or paid tier |
| **No persistent storage** | Lost on runtime termination | Not applicable (stateless service) |

---

## Troubleshooting

### "EMBEDDING_API_URL connection refused"

**Problem**: Backend can't reach the Colab tunnel

**Solution**:
1. Verify the `EMBEDDING_API_URL` in your `.env` is correct (copy-paste from Colab output)
2. Ensure the Colab cell is still running (check the tab)
3. Test manually:
   ```bash
   curl https://your-colab-tunnel.trycloudflare.com/health
   ```

### "Failed to generate embedding"

**Problem**: Colab GPU out of memory or model loading issue

**Solution**:
1. Restart the Colab runtime: **Runtime → Restart session**
2. Re-run the setup cells (dependencies + server)
3. Check GPU availability: Run `!nvidia-smi` in Colab

### "smoke-test failed"

**Problem**: Public DNS propagation delay

**Solution**:
- This usually resolves itself in 1-2 minutes
- If persistent, restart the Colab cell

---

## Alternative Hosting Providers

You can use any cloud provider with GPU support:

| Provider | Setup Complexity | Cost | URL Format |
|----------|------------------|------|-----------|
| **Google Colab** | Easy (this guide) | Free | `https://<tunnel>.trycloudflare.com` |
| **AWS Lambda** | Moderate | Pay-per-call | `https://<api-id>.lambda.<region>.amazonaws.com` |
| **Modal.com** | Moderate | Free-tier available | `https://<user>--<fn>.modal.run` |
| **Replicate** | Complex | Pay-per-call | `https://api.replicate.com/...` |
| **On-Prem Server** | Complex | Hardware cost | `https://<your-domain.com>` |

For any provider, update `.env`:
```env
EMBEDDING_API_URL=https://your-host-url/embed
```

---

## Advanced: Auto-Restart Script

To keep Colab running without manual intervention, use this script:

```python
import time

MAX_RUNTIME_HOURS = 23  # Colab timeout is 24h

start_time = time.time()
while True:
    elapsed_hours = (time.time() - start_time) / 3600
    if elapsed_hours > MAX_RUNTIME_HOURS:
        print(f"Restarting after {elapsed_hours:.1f} hours...")
        break
    print(f"Uptime: {elapsed_hours:.1f}h, tunnel active")
    time.sleep(3600)  # Check every hour
```

**Not recommended for production** — use a dedicated hosting service instead.

---

## API Reference

The embedding server exposes two endpoints:

### `/embed` (POST)

**Request:**
```json
{
  "texts": ["document text", "another text", ...]
}
```

**Response:**
```json
{
  "embeddings": [
    [0.123, 0.456, ..., -0.789],
    [0.234, 0.567, ..., -0.890],
    ...
  ]
}
```

**Embedding dimension**: 1024 (Qwen3-Embedding-0.6B)

### `/health` (GET)

**Response:**
```json
{
  "status": "ok",
  "model": "Qwen3-Embedding-0.6B",
  "device": "cuda"
}
```

---

## Related Documentation

- [Main README](../README.md) — Full project overview
- [CLAUDE.md](../CLAUDE.md) — Architecture and commands
- [Docker Compose Configuration](../docker-compose.external-embedding.yml)

---

## Verification Checklist

After setup, verify the following:

- Colab cell is running (tab is open)
- EMBEDDING_API_URL is copied to .env
- Docker stack started: docker compose -f docker-compose.yml -f docker-compose.external-embedding.yml up -d
- Backend logs show successful embedding requests: docker compose logs backend | grep embed
- Documents ingested: docker compose exec backend python -m app.scripts.ingest_all
- Frontend loads: http://localhost:3000
- Search works: Type a query and see results

---

**Last Updated**: April 2026
