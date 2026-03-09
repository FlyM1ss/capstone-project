# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ITWS 4100 (IT Capstone) project — an AI-driven company-wide search engine prototype for Deloitte. The system uses NLP with hybrid retrieval (semantic + BM25 keyword search) to let employees search internal resources via natural language queries.

**Tech stack:** Next.js 15 (App Router) + TypeScript + shadcn/ui + Vercel AI SDK frontend, FastAPI backend (Python 3.11), PostgreSQL 16 with pgvector + ParadeDB (unified hybrid search), Qwen3-Embedding-0.6B (1024-dim vectors), Cohere Rerank v3.5, Docling (document parsing), NextAuth.js (auth), Docker Compose deployment.

## Key Commands

```bash
# === Full stack (Docker) ===
docker compose up -d                    # Start all 3 services (db, backend, frontend)
docker compose down                     # Stop all services
docker compose logs -f backend          # Tail backend logs
docker compose exec backend python -m app.scripts.ingest_all  # Batch ingest demo docs

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
cd software-engineering && python3 build_docx.py
```

## Architecture

### Search Pipeline (the core flow)

```
Query → Embed (Qwen3, external service) → Parallel retrieval:
  ├─ pgvector cosine similarity (HNSW index)
  └─ ParadeDB BM25 keyword search
→ Reciprocal Rank Fusion (RRF, k=60) → Cohere Rerank v3.5 → RBAC filter → Results
```

- **Embedding model** is hosted externally (Google Colab + ngrok). Backend calls it via `EMBEDDING_API_URL`. The endpoint expects `POST {"texts": [...]}` and returns `{"embeddings": [[...]]}`.
- **Single PostgreSQL instance** (ParadeDB image) handles both vector search and BM25 — no separate vector DB.
- **BM25 index** is lazily created after the first document ingestion (`_ensure_bm25_index` in `services/ingestion.py`), not in `init.sql`.
- **Reranker** gracefully degrades: returns original order if `COHERE_API_KEY` is empty or the API call fails.
- Search tuning params are in `backend/app/core/config.py`: `SEARCH_TOP_K=50`, `RERANK_TOP_N=10`, `RRF_K=60`, `CHUNK_SIZE=512`, `CHUNK_OVERLAP=50`.

### Backend Layering

```
api/ (FastAPI routers) → services/ (business logic) → models/ (SQLAlchemy ORM + Pydantic schemas)
                                                      core/ (config, database, DI)
```

- **Routers**: `health.py`, `auth.py`, `documents.py`, `search.py` — all mounted under `/api` prefix in `main.py`
- **Services**: `search.py` (hybrid_search + RRF), `ingestion.py` (Docling parse + chunk + embed + store), `embeddings.py` (HTTP client to external model), `reranker.py` (Cohere), `auth.py` (JWT + bcrypt), `validation.py`
- **Database**: async SQLAlchemy with `asyncpg` driver. Session via `core/database.py` → `core/deps.py` (DI)
- **Models**: 4 tables — `documents`, `document_chunks` (with `vector(1024)` column), `users`, `query_logs`

### Frontend Structure

- App Router with 3 pages: landing (`/`), search results (`/search`), admin upload (`/admin/upload`)
- `lib/api.ts` — API client that calls backend via `NEXT_PUBLIC_API_URL`
- All interactive components use `"use client"` directive
- UI: shadcn/ui components + Tailwind CSS 4 + Geist font

### Auth

- JWT tokens (HS256, 60min expiry) with 3 roles:
  - `analyst` → public docs only
  - `manager` → public + internal
  - `admin` → public + internal + confidential + upload
- **Currently bypassed**: search endpoint hardcodes `user_role = "admin"` for demo purposes
- Demo users: `admin@deloitte.com` / `manager@deloitte.com` / `analyst@deloitte.com` (password: `password123`)

### Docker Services

| Service    | Image/Build       | Port | Notes                                      |
|------------|-------------------|------|--------------------------------------------|
| `db`       | paradedb/paradedb  | 5432 | Runs `backend/db/init.sql` on first start  |
| `backend`  | `./backend`       | 8000 | Volume-mounts `./backend` for hot reload   |
| `frontend` | `./frontend`      | 3000 | Volume-mounts `./frontend` for hot reload  |

## Secrets

- `.env` (root) — Database creds, Cohere API key, NextAuth secret, embedding URL. Copy from `.env.example`.
- `credentials.json` / `token.json` (in `software-engineering/`) — Google OAuth, gitignored.
- Never commit `.env`, API keys, or credential files.

## Conventions

- Monorepo: `frontend/` and `backend/` are sibling directories, orchestrated by Docker Compose
- Backend uses raw SQL (`sqlalchemy.text()`) for search queries, ORM for document/user CRUD
- Frontend API types in `lib/api.ts` mirror backend Pydantic schemas in `models/schemas.py` — keep in sync
- Diagram source of truth is `.mmd` files in `software-engineering/diagrams/`
- No test framework is set up yet (`backend/tests/` contains only `__init__.py`)
