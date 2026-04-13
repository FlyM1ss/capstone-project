# Single-Command Docker Compose Startup - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `docker compose up -d` starts the entire system (embedding server, database, backend with auto-ingestion, frontend) with zero manual steps.

**Architecture:** Add an embedding service container (CPU-only PyTorch) to Docker Compose. Wire healthchecks on all services so dependencies wait for readiness. Add a background auto-ingestion task to the FastAPI lifespan that seeds documents on first startup when the database is empty.

**Tech Stack:** Docker Compose, FastAPI lifespan, PyTorch CPU, sentence-transformers, asyncio background tasks

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `embedding.Dockerfile` | Create | Dockerfile for embedding service (CPU PyTorch + sentence-transformers) |
| `docker-compose.yml` | Modify | Add embedding service, healthchecks, dependency chain, hf_cache volume |
| `backend/Dockerfile` | Modify | Add `curl` for healthcheck |
| `backend/app/api/health.py` | Modify | Add `ingestion_status` dict and include it in health response |
| `backend/app/main.py` | Modify | Add `_auto_ingest()` background task in lifespan |
| `.env` | Modify | Update `EMBEDDING_API_URL` to Docker-internal address |

---

### Task 1: Create embedding.Dockerfile

**Files:**
- Create: `embedding.Dockerfile`

- [ ] **Step 1: Create the Dockerfile**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    torch --index-url https://download.pytorch.org/whl/cpu

RUN pip install --no-cache-dir \
    sentence-transformers \
    fastapi \
    uvicorn

COPY embedding_server.py .

EXPOSE 8001

CMD ["uvicorn", "embedding_server:app", "--host", "0.0.0.0", "--port", "8001"]
```

Write this to `embedding.Dockerfile` in the project root (same directory as `docker-compose.yml`).

Note: PyTorch is installed in a separate `RUN` layer so Docker can cache the ~1.2GB download independently from the lighter Python packages. If only `sentence-transformers` or `fastapi` versions change, the PyTorch layer is reused.

- [ ] **Step 2: Verify the Dockerfile builds**

Run:
```bash
docker build -f embedding.Dockerfile -t embedding-test .
```

Expected: Build completes successfully. The final image should be ~2-3GB (PyTorch CPU + model dependencies).

- [ ] **Step 3: Verify the container starts and serves health**

Run:
```bash
docker run --rm -p 8001:8001 -v hf_test_cache:/root/.cache/huggingface embedding-test
```

Wait for the model to download (first run: ~1-2 minutes). Then in another terminal:

```bash
curl http://localhost:8001/health
```

Expected:
```json
{"status": "ok", "model": "Qwen3-Embedding-0.6B", "device": "cpu"}
```

Stop the container with Ctrl+C after verifying.

- [ ] **Step 4: Clean up test resources**

Run:
```bash
docker rmi embedding-test
docker volume rm hf_test_cache
```

- [ ] **Step 5: Commit**

```bash
git add embedding.Dockerfile
git commit -m "feat: add embedding server Dockerfile (CPU-only PyTorch)"
```

---

### Task 2: Add curl to backend Dockerfile

**Files:**
- Modify: `backend/Dockerfile:5-7`

- [ ] **Step 1: Add curl to apt-get install**

In `backend/Dockerfile`, change line 5-7 from:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*
```

to:

```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
```

The only change is adding `curl` to the package list. This is needed for the Docker healthcheck (`CMD curl -f http://localhost:8000/api/health`).

- [ ] **Step 2: Commit**

```bash
git add backend/Dockerfile
git commit -m "feat: add curl to backend image for Docker healthcheck"
```

---

### Task 3: Add ingestion_status to health endpoint

**Files:**
- Modify: `backend/app/api/health.py:1-18`

- [ ] **Step 1: Add ingestion_status dict and include it in response**

Replace the entire contents of `backend/app/api/health.py` with:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session

router = APIRouter()

# Module-level ingestion state — updated by the auto-ingest background task in main.py
ingestion_status: dict = {"state": "idle", "done": 0, "total": 0}


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {
        "status": "ok",
        "database": db_status,
        "ingestion": ingestion_status,
    }
```

Changes from the original:
- Added `ingestion_status` dict at module level (line 10)
- Added `"ingestion": ingestion_status` to the return dict (line 24)
- Everything else unchanged

- [ ] **Step 2: Verify the health endpoint still works**

Start the backend (if running via Docker):
```bash
docker compose up -d backend
```

Then:
```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{"status": "ok", "database": "connected", "ingestion": {"state": "idle", "done": 0, "total": 0}}
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/health.py
git commit -m "feat: add ingestion status to health endpoint"
```

---

### Task 4: Add auto-ingestion to FastAPI lifespan

**Files:**
- Modify: `backend/app/main.py:1-32`

- [ ] **Step 1: Rewrite main.py with auto-ingestion lifespan**

Replace the entire contents of `backend/app/main.py` with:

```python
import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import health, auth, documents, search
from app.api.health import ingestion_status
from app.core.database import async_session
from app.services.ingestion import ingest_document

logger = logging.getLogger("uvicorn.error")

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")
CLEAN_DIRS = ["/data/sample-docs", "/data/auxiliary"]


def _collect_files(dirs: list[str]) -> list[str]:
    """Collect all supported document files from the given directories."""
    files = []
    for docs_dir in dirs:
        if not os.path.isdir(docs_dir):
            continue
        for filename in sorted(os.listdir(docs_dir)):
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                files.append(os.path.join(docs_dir, filename))
    return files


async def _auto_ingest():
    """Background task: ingest sample documents on first startup."""
    files = _collect_files(CLEAN_DIRS)
    if not files:
        logger.warning("Auto-ingest: no document files found in %s", CLEAN_DIRS)
        return

    ingestion_status["state"] = "running"
    ingestion_status["total"] = len(files)
    logger.info("Auto-ingest: starting ingestion of %d documents", len(files))

    for i, path in enumerate(files):
        filename = os.path.basename(path)
        try:
            async with async_session() as db:
                result = await ingest_document(db, path)
                if result is None:
                    logger.info("[%d/%d] %s: SKIPPED (unchanged)", i + 1, len(files), filename)
                else:
                    _, chunk_count = result
                    logger.info("[%d/%d] %s: OK (%d chunks)", i + 1, len(files), filename, chunk_count)
        except Exception as e:
            logger.error("[%d/%d] %s: ERROR - %s", i + 1, len(files), filename, e)
        ingestion_status["done"] = i + 1

    ingestion_status["state"] = "complete"
    logger.info("Auto-ingest: complete (%d/%d)", ingestion_status["done"], ingestion_status["total"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check if documents table needs seeding
    async with async_session() as db:
        result = await db.execute(text("SELECT count(*) FROM documents"))
        count = result.scalar()

    if count == 0:
        logger.info("Database is empty — starting auto-ingestion in background")
        asyncio.create_task(_auto_ingest())
    else:
        logger.info("Database has %d documents — skipping auto-ingestion", count)

    yield


app = FastAPI(
    title="Deloitte AI Search Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(search.router, prefix="/api", tags=["search"])
```

Changes from the original `main.py`:
- Added imports: `asyncio`, `logging`, `os`, `text`, `ingestion_status`, `async_session`, `ingest_document`
- Added `SUPPORTED_EXTENSIONS` and `CLEAN_DIRS` constants
- Added `_collect_files()` helper (same logic as `ingest_all.py`)
- Added `_auto_ingest()` async function that iterates files, calls `ingest_document()`, updates `ingestion_status`
- Modified `lifespan()` to check document count and spawn background task if empty
- Everything below `yield` (app creation, middleware, routers) is unchanged

- [ ] **Step 2: Verify it works with an empty database**

First, wipe the existing database and restart:
```bash
docker compose down -v
docker compose up -d db
```

Wait for db to be healthy, then start the backend:
```bash
docker compose up -d backend
```

Watch the logs:
```bash
docker compose logs -f backend
```

Expected output (after startup):
```
Database is empty — starting auto-ingestion in background
Auto-ingest: starting ingestion of N documents
[1/N] filename.pdf: OK (X chunks)
[2/N] filename.docx: OK (Y chunks)
...
Auto-ingest: complete (N/N)
```

While ingestion is running, verify the API is responsive:
```bash
curl http://localhost:8000/api/health
```

Expected:
```json
{"status": "ok", "database": "connected", "ingestion": {"state": "running", "done": 5, "total": 54}}
```

- [ ] **Step 3: Verify it skips on restart (database not empty)**

Restart the backend:
```bash
docker compose restart backend
```

Watch logs:
```bash
docker compose logs -f backend
```

Expected:
```
Database has 54 documents — skipping auto-ingestion
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: auto-ingest documents on first startup via lifespan background task"
```

---

### Task 5: Update docker-compose.yml with embedding service, healthchecks, and dependency chain

**Files:**
- Modify: `docker-compose.yml:1-55`

- [ ] **Step 1: Rewrite docker-compose.yml**

Replace the entire contents of `docker-compose.yml` with:

```yaml
services:
  db:
    image: paradedb/paradedb:latest
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-deloitte}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-deloitte_dev}
      POSTGRES_DB: ${POSTGRES_DB:-search_engine}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U deloitte -d search_engine"]
      interval: 5s
      timeout: 5s
      retries: 5

  embedding:
    build:
      context: .
      dockerfile: embedding.Dockerfile
    ports:
      - "8001:8001"
    volumes:
      - hf_cache:/root/.cache/huggingface
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 30
      start_period: 120s

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: ${DATABASE_URL}
      EMBEDDING_API_URL: ${EMBEDDING_API_URL}
      COHERE_API_KEY: ${COHERE_API_KEY}
    volumes:
      - ./backend:/app
      - ./data:/data
      - model_cache:/root/.EasyOCR
    depends_on:
      db:
        condition: service_healthy
      embedding:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
      interval: 5s
      timeout: 5s
      retries: 5

  frontend:
    build:
      context: ./Fetch
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
    volumes:
      - ./Fetch:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      backend:
        condition: service_healthy

volumes:
  pgdata:
  model_cache:
  hf_cache:
```

Changes from the original:
- Added `embedding` service block (lines 20-31) with build, ports, volume, and healthcheck
- Added `healthcheck` to `backend` (lines 51-55)
- Changed `backend.depends_on` from just `db: condition: service_healthy` to also include `embedding: condition: service_healthy` (lines 46-49)
- Changed `backend.environment.EMBEDDING_API_URL` from hardcoded `http://host.docker.internal:8001/embed` to `${EMBEDDING_API_URL}` (reads from `.env`)
- Changed `frontend.depends_on` from `- backend` to `backend: condition: service_healthy` (lines 66-67)
- Added `hf_cache` to the `volumes` section (line 72)

- [ ] **Step 2: Commit**

```bash
git add docker-compose.yml
git commit -m "feat: add embedding service, healthchecks, and dependency chain to docker-compose"
```

---

### Task 6: Update .env with Docker-internal embedding URL

**Files:**
- Modify: `.env:5`

- [ ] **Step 1: Update EMBEDDING_API_URL**

In `.env`, change line 5 from:

```
EMBEDDING_API_URL=http://host.docker.internal:8001/embed
```

to:

```
EMBEDDING_API_URL=http://embedding:8001/embed
```

This points to the Docker-internal embedding service hostname instead of the host machine.

- [ ] **Step 2: Commit**

```bash
git add .env
git commit -m "chore: point EMBEDDING_API_URL to Docker-internal embedding service"
```

---

### Task 7: End-to-end verification

**Files:** None (verification only)

This task validates the entire startup flow works with a single command.

- [ ] **Step 1: Clean slate**

Stop all containers and remove volumes (fresh start):

```bash
docker compose down -v
```

- [ ] **Step 2: Build and start everything**

```bash
docker compose up -d --build
```

Expected: All 4 services start. `db` and `embedding` start in parallel, `backend` waits for both, `frontend` waits for `backend`.

- [ ] **Step 3: Monitor startup**

Watch all service logs:

```bash
docker compose logs -f
```

Expected sequence:
1. `db` logs: "database system is ready to accept connections"
2. `embedding` logs: "Loading Qwen3-Embedding-0.6B on CPU..." then "Model loaded on CPU -- ready to serve embeddings"
3. `backend` logs: "Database is empty -- starting auto-ingestion in background"
4. `backend` logs: "[1/N] filename: OK (X chunks)" ... progressing through all documents
5. `backend` logs: "Auto-ingest: complete (N/N)"
6. `frontend` logs: dev server ready on port 3000

- [ ] **Step 4: Verify all services are healthy**

```bash
docker compose ps
```

Expected: All 4 services show status `healthy` (or `running` for frontend which has no healthcheck).

- [ ] **Step 5: Verify health endpoint shows ingestion progress**

While ingestion is running (or after):

```bash
curl http://localhost:8000/api/health
```

Expected (during ingestion):
```json
{"status": "ok", "database": "connected", "ingestion": {"state": "running", "done": 12, "total": 54}}
```

Expected (after ingestion):
```json
{"status": "ok", "database": "connected", "ingestion": {"state": "complete", "done": 54, "total": 54}}
```

- [ ] **Step 6: Verify search works after ingestion completes**

Wait for ingestion to finish (check health endpoint or logs), then:

```bash
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly report"}'
```

Expected: JSON response with `results` array containing relevant documents.

- [ ] **Step 7: Verify frontend loads**

Open `http://localhost:3000` in a browser. The landing page should load. Search for "quarterly report" and verify results appear.

- [ ] **Step 8: Verify restart skips ingestion**

```bash
docker compose restart backend
docker compose logs -f backend
```

Expected: "Database has N documents -- skipping auto-ingestion"

- [ ] **Step 9: Verify second `docker compose up` is fast (no rebuild)**

```bash
docker compose down
docker compose up -d
```

Expected: All services start within ~30 seconds (no image rebuilds, model loaded from hf_cache volume).

---

### Task 8: Update CLAUDE.md with new startup instructions

**Files:**
- Modify: `CLAUDE.md`

- [ ] **Step 1: Update the Key Commands section**

In the root `CLAUDE.md`, update the "Full stack (Docker)" section to reflect the new single-command startup. Replace the existing commands block:

```bash
# === Full stack (Docker) ===
docker compose up -d                    # Start all 4 services (db, embedding, backend, frontend)
                                        # First run: downloads embedding model (~600MB) + auto-ingests documents
                                        # Subsequent runs: starts in ~30s, skips ingestion
docker compose up -d --build            # Rebuild images (only needed after requirements.txt/package.json changes)
docker compose down                     # Stop all services
docker compose down -v                  # Stop all services + delete all data (fresh start)
docker compose logs -f backend          # Tail backend logs (shows ingestion progress)
docker compose exec backend python -m app.scripts.ingest_all              # Re-ingest clean data (manual)
docker compose exec backend python -m app.scripts.ingest_all --poisoned   # Ingest poisoned data only (adversarial test)
docker compose exec backend python -m app.scripts.ingest_all --all        # Ingest everything (clean + poisoned)
docker compose exec backend python -m app.scripts.ingest_all --clean      # Wipe DB + re-ingest clean data
```

- [ ] **Step 2: Update the Docker Services table**

Replace the existing table with:

| Service     | Image/Build        | Port | Notes                                                      |
|-------------|-------------------|------|--------------------------------------------------------------|
| `db`        | paradedb/paradedb  | 5432 | Runs `init.sql` on first start, `pgdata` volume             |
| `embedding` | `./embedding.Dockerfile` | 8001 | CPU-only PyTorch, Qwen3-Embedding-0.6B, `hf_cache` volume   |
| `backend`   | `./backend`        | 8000 | Auto-ingests on first start, mounts `./data`                 |
| `frontend`  | `./Fetch`          | 3000 | Bun-based dev container                                      |

- [ ] **Step 3: Update the Architecture > Search Pipeline section**

Replace the embedding model bullet point:

```
- **Embedding model** runs as the `embedding` Docker service (CPU-only, auto-starts with `docker compose up`). Backend calls it via `EMBEDDING_API_URL` (default `http://embedding:8001/embed` inside Docker). The endpoint expects `POST {"texts": [...]}` and returns `{"embeddings": [[...]]}`. For standalone dev, override to `http://localhost:8001/embed`.
```

- [ ] **Step 4: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for single-command Docker startup"
```
