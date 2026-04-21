# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ITWS 4100 (IT Capstone) project — an AI-driven company-wide search engine prototype for Deloitte. The system uses NLP with hybrid retrieval (semantic + BM25 keyword search) to let employees search internal resources via natural language queries.

**Tech stack:** Next.js 16 (App Router) + TypeScript + shadcn/ui (@base-ui/react primitives) frontend, FastAPI backend (Python 3.11), PostgreSQL 16 with pgvector + ParadeDB (unified hybrid search), Qwen3-Embedding-0.6B (1024-dim vectors), Cohere Rerank v3.5, Docling (document parsing), JWT auth (backend-issued, bcrypt + HS256), Docker Compose deployment.

## Key Commands

```bash
# === Full stack (Docker) ===
docker compose up -d                    # Start all 4 services (db, embedding, backend, frontend)
                                        # First run: downloads embedding model (~600MB)
                                        # Does NOT auto-ingest; run ingest_all manually after first start
docker compose up -d --build            # Rebuild images (only needed after requirements.txt/package.json changes)
docker compose down                     # Stop all services
docker compose down -v                  # Stop all services + delete all data (fresh start)
docker compose logs -f backend          # Tail backend logs (shows ingestion progress)
docker compose exec backend python -m app.scripts.ingest_all              # Re-ingest clean data (generic + auxiliary)
docker compose exec backend python -m app.scripts.ingest_all --poisoned   # Adversarial data (malformed + prompt-injected + legacy poisoned)
docker compose exec backend python -m app.scripts.ingest_all --all        # Ingest everything
docker compose exec backend python -m app.scripts.ingest_all --clean      # Wipe DB + re-ingest using selected mode

# Optional ingest targeting/settings:
docker compose exec backend python -m app.scripts.ingest_all --mode malformed
docker compose exec backend python -m app.scripts.ingest_all --mode prompt-injected
docker compose exec backend python -m app.scripts.ingest_all --categories generic malformed
docker compose exec backend python -m app.scripts.ingest_all --recursive --limit 25

# === Backend standalone ===
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# === Frontend standalone ===
cd frontend
bun install
bun run dev              # Dev server on :3000
bun run build            # Production build
bun run lint             # ESLint

# === API quick tests ===
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly report"}'
curl -X POST http://localhost:8000/api/documents -F "file=@path/to/file.pdf"

# === Software engineering deliverable ===
cd coursework/software-engineering && python3 build_docx.py
```

## Architecture

### Search Pipeline (the core flow)

```
Query → Embed (Qwen3, external service) → Parallel retrieval:
  ├─ pgvector cosine similarity on chunks (HNSW index)
  ├─ ParadeDB BM25 keyword search on chunks
  └─ pgvector cosine similarity on title embeddings (HNSW index)
→ Weighted RRF merge (3 lists, title_weight=1.5) → Batch doc fetch → Cohere Rerank v3.5
→ Version filter (show_latest_only) → RBAC filter → Results
```

- **Embedding model** runs as the `embedding` Docker service (GPU-accelerated via NVIDIA Container Toolkit, auto-starts with `docker compose up`). Backend calls it via `EMBEDDING_API_URL` (default `http://embedding:8001/embed` inside Docker). The endpoint expects `POST {"texts": [...]}` and returns `{"embeddings": [[...]]}`. For standalone dev, override to `http://localhost:8001/embed`. Requires an NVIDIA GPU and `nvidia-container-toolkit` on the host.
- **Single PostgreSQL instance** (ParadeDB image) handles both vector search and BM25 — no separate vector DB.
- **Title embeddings** stored in separate `document_title_embeddings` table with its own HNSW index for clean separation from chunk embeddings.
- **BM25 index** is lazily created after the first document ingestion (`_ensure_bm25_index` in `services/ingestion.py`), not in `init.sql`.
- **Reranker** gracefully degrades: returns original order if `COHERE_API_KEY` is empty or the API call fails.
- **Version-aware ranking**: Documents are linked via `document_group` column. Version detected from `_v(\d+)` filename suffix at ingestion. "Show latest only" filter (on by default) hides superseded versions post-rerank.
- Search tuning params are in `backend/app/core/config.py`: `SEARCH_TOP_K=50`, `RERANK_TOP_N=10`, `RRF_K=60`, `CHUNK_SIZE=512`, `CHUNK_OVERLAP=50`, `TITLE_BOOST_WEIGHT=1.5`, `EMBED_BATCH_SIZE=64`.

### Backend Layering

```
api/ (FastAPI routers) → services/ (business logic) → models/ (SQLAlchemy ORM + Pydantic schemas)
                                                      core/ (config, database, DI)
```

- **Routers**: `health.py`, `auth.py`, `documents.py`, `search.py` — all mounted under `/api` prefix in `main.py`
- **Services**: `search.py` (hybrid_search + RRF), `ingestion.py` (Docling parse + chunk + embed + store), `embeddings.py` (HTTP client to external model), `reranker.py` (Cohere), `auth.py` (JWT + bcrypt), `validation.py`
- **Database**: async SQLAlchemy with `asyncpg` driver. Session via `core/database.py` → `core/deps.py` (DI)
- **Models**: 5 tables — `documents` (with `document_group` + `version`), `document_chunks` (with `vector(1024)` column), `document_title_embeddings` (with `vector(1024)` column), `users`, `query_logs`

### Frontend Structure

- App Router with 3 pages: landing (`/`), search results (`/search`), admin upload (`/admin/upload`)
- `lib/api.ts` — API client that calls backend via `NEXT_PUBLIC_API_URL`
- 5 custom components (`search-bar`, `result-card`, `filter-panel`, `file-upload`, `search-tips`) + shadcn/ui primitives
- UI: shadcn/ui components (@base-ui/react, not Radix) + Tailwind CSS 4 + Geist font + lucide-react icons

### Auth

- **Backend JWT auth** (`services/auth.py`): bcrypt password hashing + HS256 JWT tokens (60min expiry)
- 3 roles with RBAC filtering in search:
  - `analyst` → public docs only
  - `manager` → public + internal
  - `admin` → public + internal + confidential + upload
- **Currently bypassed**: search endpoint hardcodes `user_role = "admin"` for demo purposes
- `next-auth` is installed in the frontend but not wired up (no config, no API routes, no middleware)
- Demo users: `admin@deloitte.com` / `manager@deloitte.com` / `analyst@deloitte.com` (password: `password123`)

### Docker Services

| Service     | Image/Build        | Port | Notes                                                      |
|-------------|-------------------|------|--------------------------------------------------------------|
| `db`        | paradedb/paradedb  | 5432 | Runs `init.sql` on first start, `pgdata` volume             |
| `embedding` | `./embedding.Dockerfile` | 8001 | CUDA PyTorch + GPU passthrough, Qwen3-Embedding-0.6B, `hf_cache` volume |
| `backend`   | `./backend`        | 8000 | Auto-ingests on first start, mounts `./data`                 |
| `frontend`  | `./frontend`       | 3000 | Bun-based dev container                                      |

## Secrets

- `.env` (root) — Database creds, Cohere API key, NextAuth secret, embedding URL. Copy from `.env.example`.
- `credentials.json` / `token.json` (in `coursework/software-engineering/`) — Google OAuth, gitignored.
- Never commit `.env`, API keys, or credential files.

## Conventions

- Monorepo: `frontend/` and `backend/` are sibling directories, orchestrated by Docker Compose
- Backend uses raw SQL (`sqlalchemy.text()`) for search queries, ORM for document/user CRUD
- Frontend API types in `lib/api.ts` mirror backend Pydantic schemas in `models/schemas.py` — keep in sync
- Diagram source of truth is `.mmd` files in `coursework/software-engineering/diagrams/`
- No test framework is set up yet (`backend/tests/` contains only `__init__.py`)
