# Single-Command Docker Compose Startup

**Date:** 2026-04-13
**Status:** Approved
**Goal:** `docker compose up -d` starts the entire system, including embedding inference, database seeding, and all application services, with zero manual steps.

## Current State (3 manual steps)

```
1. python embedding_server.py                                    # host or Colab
2. docker compose up -d                                          # db + backend + frontend
3. docker compose exec backend python -m app.scripts.ingest_all  # seed documents
```

## Target State (1 command)

```
docker compose up -d
# db + embedding start in parallel
# backend starts after both are healthy
# backend auto-ingests documents in background (if DB is empty)
# frontend starts after backend is healthy
# ~2-3 min later: 54 documents ingested, search fully operational
```

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Embedding server | Include in Docker Compose (CPU-only) | True single-command startup; CPU inference is fast enough for 0.6B model |
| Ingestion behavior | Background task, API available immediately | Best developer/demo UX; partial results acceptable during loading |
| Ingestion approach | FastAPI lifespan background task | No extra containers or scripts; reuses existing ingestion code; dedup-safe |

## Architecture

### Service Dependency Chain

```
db (healthy) ──────┐
                   ├──> backend (healthy) ──> frontend
embedding (healthy)┘
```

- `db` and `embedding` start in parallel (no dependency between them)
- `backend` waits for both to be healthy before starting
- `frontend` waits for `backend` to be healthy before starting

### Startup Timeline (approximate)

| Time | Event |
|------|-------|
| 0s | `docker compose up -d` issued |
| 0-5s | `db` and `embedding` containers start |
| 5-10s | `db` becomes healthy (pg_isready) |
| 10-120s | `embedding` downloads model (first run only; cached after) |
| ~15s (repeat) / ~120s (first) | `embedding` becomes healthy |
| +2-3s | `backend` starts, detects empty DB, spawns background ingestion |
| +1s | `backend` health endpoint returns 200, `frontend` starts |
| +2-3 min | Background ingestion completes all 54 documents |

## Design: Section 1 - Embedding Service Container

### New file: `embedding.Dockerfile`

- Base image: `python:3.11-slim`
- Installs: `curl` (for healthcheck), CPU-only PyTorch (`--index-url https://download.pytorch.org/whl/cpu`), `sentence-transformers`, `fastapi`, `uvicorn`
- Copies `embedding_server.py` from project root
- CMD: `uvicorn embedding_server:app --host 0.0.0.0 --port 8001`

### docker-compose.yml service definition

```yaml
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
```

- **CPU-only PyTorch** reduces image from ~3GB to ~1.2GB
- **`hf_cache` volume** persists Qwen3 model weights (~600MB); first run downloads, subsequent runs load from cache
- **`start_period: 120s`** gives time for first-time model download without counting health failures

## Design: Section 2 - Healthchecks & Dependencies

### Backend healthcheck (new)

```yaml
backend:
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/api/health"]
    interval: 5s
    timeout: 5s
    retries: 5
  depends_on:
    db:
      condition: service_healthy
    embedding:
      condition: service_healthy
```

### Backend Dockerfile change

Add `curl` to the existing `apt-get install` line:
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev curl \
    && rm -rf /var/lib/apt/lists/*
```

### Frontend dependency (updated)

```yaml
frontend:
  depends_on:
    backend:
      condition: service_healthy   # was: just "- backend"
```

## Design: Section 3 - Auto-Ingestion via FastAPI Lifespan

### Modified file: `backend/app/main.py`

The currently-empty `lifespan` function gets auto-ingestion logic:

1. On startup, query `SELECT count(*) FROM documents`
2. If count is 0, spawn `asyncio.create_task(_auto_ingest())`
3. If count > 0, log "Database already has N documents, skipping ingestion"
4. `yield` immediately so uvicorn starts accepting requests

### `_auto_ingest()` function (in `main.py`)

- Collects files from `/data/sample-docs` and `/data/auxiliary` (clean data only)
- Filters for `.pdf`, `.docx`, `.pptx` extensions
- Iterates files sequentially, calling `ingest_document()` from existing `app.services.ingestion`
- Each file gets its own database session (one failure doesn't roll back others)
- Updates `ingestion_status` dict in `app.api.health` for progress tracking
- Logs progress to stdout (visible via `docker compose logs -f backend`)

### Safety properties

- **Idempotent:** Only runs when `documents` table is empty (count == 0)
- **Dedup-safe:** `ingest_document()` checks `content_hash` before parsing, so restarts mid-ingestion skip already-processed files
- **Clean data only:** Poisoned data (`/data/poisoned/`) still requires manual `--poisoned` flag via `ingest_all` script

## Design: Section 4 - Environment & Config Changes

### docker-compose.yml backend environment

```yaml
EMBEDDING_API_URL: http://embedding:8001/embed   # was: http://host.docker.internal:8001/embed
```

### `.env` file

```
EMBEDDING_API_URL=http://embedding:8001/embed
```

The `docker-compose.yml` `environment` block for the backend should reference this via `${EMBEDDING_API_URL}` (it already does) so the `.env` value is the single source of truth. No hardcoded override in docker-compose.yml.

Note: Standalone (non-Docker) backend dev requires overriding this to `http://localhost:8001/embed` via a local `.env` or shell export.

### New volume

```yaml
volumes:
  pgdata:
  model_cache:
  hf_cache:       # persists Hugging Face model weights for embedding service
```

### No changes needed to

- `backend/app/core/config.py` (already reads `EMBEDDING_API_URL` from env)
- `backend/app/services/embeddings.py` (already uses `settings.EMBEDDING_API_URL`)
- Frontend code (doesn't talk to embedding service)

## Design: Section 5 - Health Endpoint Enhancement

### Modified file: `backend/app/api/health.py`

Add module-level `ingestion_status` dict:

```python
ingestion_status = {"state": "idle", "done": 0, "total": 0}
```

The health endpoint returns this alongside the existing status:

```json
{"status": "ok", "ingestion": {"state": "running", "done": 12, "total": 54}}
```

States: `"idle"` (default/no ingestion needed), `"running"` (in progress), `"complete"` (finished).

The `_auto_ingest()` task in `main.py` imports and updates this dict as it progresses. No database queries on health checks; just reads an in-memory dict.

The Docker healthcheck still passes during ingestion (returns 200 regardless of ingestion state) since the API is genuinely healthy and ready to serve requests.

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `embedding.Dockerfile` | Create | CPU-only PyTorch + sentence-transformers + embedding_server.py |
| `docker-compose.yml` | Edit | Add embedding service, healthchecks, dependency chain, update env vars, add hf_cache volume |
| `backend/Dockerfile` | Edit | Add `curl` to apt-get install |
| `backend/app/main.py` | Edit | Add auto-ingestion background task in lifespan |
| `backend/app/api/health.py` | Edit | Add ingestion_status dict and return it in health response |
| `.env` | Edit | Update EMBEDDING_API_URL to Docker-internal address |

## What This Does NOT Change

- **Manual ingestion still works:** `docker compose exec backend python -m app.scripts.ingest_all` remains functional for re-ingestion or poisoned data
- **Standalone dev:** Running backend/frontend outside Docker still works; just override EMBEDDING_API_URL
- **Existing search pipeline:** No changes to search, reranking, or RBAC logic
- **Frontend code:** No changes needed
