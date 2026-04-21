# Capstone Project — Comprehensive Status Report
*Generated: 2026-03-22*

---

## Project Overview

**Name:** AI-Driven Company-Wide Search Engine (Deloitte Prototype)
**Course:** ITWS 4100 — IT & Web Science Capstone, RPI Spring 2026
**Status:** MVP/Prototype — core search pipeline fully functional, some features demo-only

**Tech Stack:**
- Frontend: Next.js 15 (App Router) + TypeScript + React 19 + shadcn/ui + Tailwind CSS 4 + Vercel AI SDK
- Backend: FastAPI (Python 3.11) + SQLAlchemy 2.0 (async) + asyncpg
- Database: PostgreSQL 16 via ParadeDB image (pgvector + BM25 in one instance)
- Embedding Model: Qwen3-Embedding-0.6B (1024-dim), hosted externally on port 8001
- Reranker: Cohere Rerank v3.5
- Document Parsing: Docling 2.31.0
- Auth: JWT (python-jose) + bcrypt (passlib) + NextAuth.js (installed but unused in UI)
- Deployment: Docker Compose (3 containers)

---

## Directory Structure

```
capstone-project/
├── frontend/                        # Next.js 15 frontend
│   ├── app/
│   │   ├── page.tsx                 # Landing page
│   │   ├── layout.tsx
│   │   ├── globals.css
│   │   ├── search/page.tsx          # Search results page
│   │   └── admin/upload/page.tsx    # Document upload admin page
│   ├── components/
│   │   ├── search-bar.tsx
│   │   ├── search-tips.tsx
│   │   ├── result-card.tsx
│   │   ├── filter-panel.tsx
│   │   ├── file-upload.tsx
│   │   └── ui/                      # shadcn/ui component library
│   ├── lib/
│   │   ├── api.ts                   # API client (all backend calls)
│   │   └── utils.ts
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── components.json
│   └── Dockerfile                   # oven/bun:1-alpine
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + CORS + router mounts
│   │   ├── core/
│   │   │   ├── config.py            # Pydantic settings (all tuning params)
│   │   │   ├── database.py          # Async SQLAlchemy session
│   │   │   └── deps.py              # DI exports
│   │   ├── models/
│   │   │   ├── db.py                # SQLAlchemy ORM (5 tables)
│   │   │   └── schemas.py           # Pydantic request/response schemas
│   │   ├── api/
│   │   │   ├── health.py            # GET /api/health
│   │   │   ├── auth.py              # POST /api/auth/login
│   │   │   ├── documents.py         # GET/POST /api/documents, GET /api/documents/{id}
│   │   │   └── search.py            # POST /api/search
│   │   ├── services/
│   │   │   ├── search.py            # Hybrid search + RRF merge (268 lines)
│   │   │   ├── ingestion.py         # Docling parse + chunk + embed + store (157 lines)
│   │   │   ├── embeddings.py        # HTTP client to Qwen3 server
│   │   │   ├── reranker.py          # Cohere Rerank with graceful fallback
│   │   │   ├── auth.py              # JWT + bcrypt logic
│   │   │   └── validation.py        # Query injection checks
│   │   └── scripts/
│   │       └── ingest_all.py        # Batch ingestion (--poisoned / --all flags)
│   ├── db/
│   │   └── init.sql                 # Schema + HNSW indexes + seed users
│   ├── tests/
│   │   └── __init__.py              # STUB ONLY — no tests
│   ├── requirements.txt
│   └── Dockerfile                   # python:3.11-slim
├── embedding_server.py              # Standalone Qwen3-Embedding-0.6B FastAPI server
├── docker-compose.yml               # 3 services: db, backend, frontend
├── .env                             # Secrets (gitignored)
├── .env.example                     # Template
├── CLAUDE.md                        # Architecture reference
├── docs/
│   ├── plans/                       # MVP design docs (2026-03-09)
│   └── superpowers/specs/           # Title boosting + version ranking design
├── mini-strategic-plan/
│   └── Mini_Strategic_Plan.md
├── software-engineering/            # SE deliverables (DOCX build script)
├── Pre-Project-Research/
├── Proposal/
└── CostBenefitAnalysis/
```

---

## What Is Fully Implemented

### Backend

| Component | Status | Notes |
|-----------|--------|-------|
| FastAPI app + CORS | ✅ Complete | Mounts all routers under `/api` |
| Health check (`GET /api/health`) | ✅ Complete | Returns DB connectivity status |
| Login endpoint (`POST /api/auth/login`) | ✅ Complete | JWT HS256, 60min expiry, bcrypt verify |
| JWT token creation & validation | ✅ Complete | `services/auth.py` |
| Document upload (`POST /api/documents`) | ✅ Complete | Accepts PDF/DOCX/PPTX, triggers ingestion |
| Document list (`GET /api/documents`) | ✅ Complete | Returns all documents |
| Document detail (`GET /api/documents/{id}`) | ✅ Complete | Returns single document |
| Document parsing (Docling) | ✅ Complete | PDF, DOCX, PPTX → Markdown |
| Chunking (word-based, overlapping) | ✅ Complete | 512-word chunks, 50-word overlap |
| Embedding (Qwen3-0.6B) | ✅ Complete | External HTTP call to port 8001 |
| Batch embed (title + chunks together) | ✅ Complete | Minimizes API call overhead |
| BM25 keyword search (ParadeDB) | ✅ Complete | Lazy index creation on first ingest |
| Semantic vector search (pgvector) | ✅ Complete | HNSW index, cosine similarity |
| Title embedding search | ✅ Complete | Separate table + HNSW index |
| RRF merge (3 signals) | ✅ Complete | Weighted, title_weight=1.5 |
| Cohere Rerank v3.5 | ✅ Complete | Graceful fallback if key missing |
| Version-aware documents | ✅ Complete | `_v(\d+)` filename detection, document_group |
| "Show latest only" filter | ✅ Complete | Post-rerank version filter |
| RBAC logic (service layer) | ✅ Complete | 3 roles: analyst/manager/admin |
| Query input validation | ✅ Complete | 4 injection pattern checks |
| Database schema + indexes | ✅ Complete | 5 tables, HNSW x2, BM25, access indexes |
| Seed users in DB | ✅ Complete | 3 demo accounts, bcrypt-hashed |
| Batch ingestion script | ✅ Complete | `ingest_all.py` with --poisoned/--all modes |
| Version detection at ingest | ✅ Complete | Auto-increments version on re-ingest |
| Embedding server | ✅ Complete | `embedding_server.py`, auto GPU/CPU |

### Frontend

| Component | Status | Notes |
|-----------|--------|-------|
| Landing page (`/`) | ✅ Complete | Search bar, example queries |
| Search results page (`/search?q=...`) | ✅ Complete | Results + filter panel |
| Admin upload page (`/admin/upload`) | ✅ Complete | Drag-and-drop, progress tracking |
| `SearchBar` component | ✅ Complete | Form submit, connects to search page |
| `SearchTips` popup | ✅ Complete | Collapsible example queries |
| `ResultCard` component | ✅ Complete | Title, snippet, metadata, version badge |
| `FilterPanel` component | ✅ Complete | Category, doc type, "Latest only" toggle |
| `FileUpload` component | ✅ Complete | Drag-drop + click, progress status |
| API client (`lib/api.ts`) | ✅ Complete | `searchDocuments`, `listDocuments`, `uploadDocument` |

### Infrastructure

| Component | Status | Notes |
|-----------|--------|-------|
| Docker Compose | ✅ Complete | 3 services with health checks + depends_on |
| Backend Dockerfile | ✅ Complete | python:3.11-slim, hot reload |
| Frontend Dockerfile | ✅ Complete | bun:1-alpine, hot reload |
| Database init (init.sql) | ✅ Complete | Schema + seed data on first start |
| Environment config | ✅ Complete | `.env.example` template provided |

---

## What Is Partially Implemented (Stubs / Bypassed)

### 1. Auth Integration in Search (`backend/app/api/search.py:21`)
- **What exists:** Full JWT token creation, login endpoint, `get_user_from_token()` function all work.
- **What's missing:** The search endpoint extracts no token from request headers. It hardcodes `user_role = "admin"`.
- **Impact:** Every user gets admin-level results. RBAC access control logic in `services/search.py` is dead code at runtime.
- **Fix:** Add `Authorization: Bearer ...` header extraction and call `auth.get_user_from_token()`.

### 2. Query Logging (`models/db.py` → `QueryLog` table)
- **What exists:** `QueryLog` table (id, user_id, query_text, result_count, selected_doc_id, latency_ms) is defined in ORM and `init.sql`.
- **What's missing:** Nothing ever writes to it. No code path calls `INSERT INTO query_logs`.
- **Impact:** No search analytics, no audit trail.

### 3. NextAuth.js Session Management
- **What exists:** `next-auth` is installed in `package.json`.
- **What's missing:** No `[...nextauth]` route handler, no `SessionProvider` in layout, no `useSession()` usage.
- **Impact:** Login page was removed (commit `06ba9c4`). Auth tokens can't be passed from frontend to backend.

### 4. Frontend Auth Token Passing
- **What exists:** `searchDocuments(query, filters?, token?, showLatestOnly?)` has a `token` parameter in `lib/api.ts`. It sends `Authorization: Bearer ${token}` if provided.
- **What's missing:** No session system to supply that token. The token is always `undefined`.

---

## What Is Not Implemented

| Feature | Notes |
|---------|-------|
| Document detail page (`/documents/[id]`) | Designed in MVP doc, route not created |
| Search pagination | No offset/limit, always returns top_k |
| User creation API endpoint | Users seeded in DB only; no POST /api/users |
| Admin-only protection on upload | `POST /api/documents` has no auth check |
| Rate limiting | No middleware on any endpoint |
| Test suite | `backend/tests/` has only `__init__.py` |
| Query analytics dashboard | QueryLog table exists but is never written to |
| Monitoring / alerting | No logging beyond uvicorn stdout |
| Production deployment guide | Dev-only Docker Compose, no production hardening |
| Secrets management | API keys in `.env` file (Cohere key visible) |
| Error feedback to user | Some catch blocks are silent (BM25, title search) |

---

## API Endpoints Reference

| Method | Path | Auth Required | Status |
|--------|------|---------------|--------|
| `GET` | `/api/health` | None | ✅ Full |
| `POST` | `/api/auth/login` | None (sends credentials) | ✅ Full |
| `POST` | `/api/search` | None enforced (hardcoded admin) | ⚠️ Bypassed |
| `GET` | `/api/documents` | None | ✅ Full |
| `POST` | `/api/documents` | None enforced | ⚠️ Unprotected |
| `GET` | `/api/documents/{id}` | None | ✅ Full |

---

## Search Pipeline (End-to-End Connected)

```
User Query (frontend)
  → POST /api/search (search.py router)
  → services/validation.py  [injection pattern check]
  → services/embeddings.py  [POST http://host.docker.internal:8001/embed]
  → Parallel SQL:
      ├─ pgvector cosine sim on document_chunks.embedding (top 50)
      ├─ ParadeDB BM25 on document_chunks.content (top 50)
      └─ pgvector cosine sim on document_title_embeddings.embedding (top 50)
  → RRF merge (k=60, title weight=1.5x)
  → Cohere Rerank v3.5 (or passthrough fallback)
  → Version filter (show_latest_only: hide superseded)
  → RBAC filter (currently always admin → no filtering)
  → Return SearchResponse {results, total, latency_ms}
```

The search pipeline is **fully connected end-to-end** as long as the embedding server (port 8001) is running. Reranker gracefully degrades if Cohere key is absent.

---

## Database Schema

### Tables

| Table | Columns | Purpose |
|-------|---------|---------|
| `documents` | id, title, author, doc_type, category, created_date, access_level, file_path, page_count, document_group, version | Core document metadata + versioning |
| `document_chunks` | id, document_id(FK), chunk_index, content, embedding(1024), metadata(JSONB) | Chunked text + vectors |
| `document_title_embeddings` | id, document_id(FK unique), title_text, embedding(1024) | Per-document title vectors |
| `users` | id, email(unique), name, hashed_password, role | Auth / RBAC |
| `query_logs` | id, user_id(FK), query_text, result_count, selected_doc_id, latency_ms | Analytics (never written to) |

### Indexes

| Index | Type | Columns |
|-------|------|---------|
| Semantic search | HNSW | `document_chunks.embedding` (m=16, ef_construction=200) |
| Title search | HNSW | `document_title_embeddings.embedding` |
| BM25 | Tantivy (ParadeDB) | `document_chunks.content` — lazy, created at first ingest |
| Access filter | B-tree | `documents.access_level` |
| Category filter | B-tree | `documents.category` |
| Version grouping | B-tree | `documents.document_group` |

---

## Key Configuration Parameters

All tunable in `backend/app/core/config.py`:

```python
EMBEDDING_API_URL: str = "http://localhost:8001/embed"  # Override in .env for Docker
COHERE_API_KEY: str = ""                                 # Reranker (optional)
SEARCH_TOP_K: int = 50                                   # Candidates per retrieval path
RERANK_TOP_N: int = 10                                   # Final results after rerank
RRF_K: int = 60                                          # RRF smoothing constant
CHUNK_SIZE: int = 512                                    # Words per chunk
CHUNK_OVERLAP: int = 50                                  # Overlap words between chunks
TITLE_BOOST_WEIGHT: float = 1.5                          # Title signal multiplier in RRF
```

---

## Dependencies

### Backend (requirements.txt)

```
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]==2.0.41
asyncpg==0.30.0
psycopg2-binary==2.9.10
pgvector==0.3.6
pydantic-settings==2.9.1
python-multipart==0.0.20
docling==2.31.0
cohere==5.15.0
httpx==0.28.1
python-jose[cryptography]==3.4.0
passlib[bcrypt]==1.7.4
```

### Frontend (package.json key deps)

```json
"next": "16.1.6",
"react": "19.2.3",
"@ai-sdk/react": "^3.0.118",
"ai": "^6.0.116",
"next-auth": "^4.24.13",
"lucide-react": "^0.577.0",
"shadcn": "^4.0.2",
"tailwind-merge": "^3.5.0"
```

---

## Hardcoded Values / Technical Debt

| Location | Issue | Impact |
|----------|-------|--------|
| `backend/app/api/search.py:21` | `user_role = "admin"` hardcoded | RBAC bypassed for all users |
| `backend/app/services/auth.py:13` | `SECRET_KEY = "dev-secret-key-change-in-production"` | Should come from `.env` |
| `frontend/components/filter-panel.tsx` | Categories and doc types are hardcoded arrays | Breaks if new types are ingested |
| `backend/app/core/config.py` | `EMBEDDING_API_URL` defaults to `localhost` | Fails in Docker without `.env` override |
| `.env` | Cohere API key in plaintext file | Should use secrets manager in production |

---

## Docker Setup

### Services

| Service | Image | Port | Depends On |
|---------|-------|------|------------|
| `db` | `paradedb/paradedb:latest` | 5432 | — |
| `backend` | `./backend` (python:3.11-slim) | 8000 | `db` (healthy) |
| `frontend` | `./frontend` (bun:1-alpine) | 3000 | `backend` |

### Key Commands

```bash
docker compose up -d
docker compose down
docker compose logs -f backend
docker compose exec backend python -m app.scripts.ingest_all
docker compose exec backend python -m app.scripts.ingest_all --all
```

### Notes
- The embedding server (`embedding_server.py`) runs **outside** Docker on port 8001. The `.env` sets `EMBEDDING_API_URL=http://host.docker.internal:8001/embed` to bridge this.
- `./data` directory is volume-mounted into the backend container for ingestion.
- Hot reload is active in both backend (uvicorn --reload) and frontend (bun run dev).

---

## Test Coverage

**Coverage: 0%**

- `backend/tests/__init__.py` is an empty stub.
- No test framework configured (no pytest, no jest/vitest).
- No unit tests, integration tests, or end-to-end tests exist.

---

## Known Issues Summary

1. **RBAC bypassed** — `user_role = "admin"` hardcoded in search endpoint. All documents visible to all users.
2. **Auth not wired to frontend** — Sign-in page removed, NextAuth.js installed but unused.
3. **Query logging never fires** — `QueryLog` table defined, nothing ever inserts into it.
4. **Embedding server is external dependency** — If port 8001 is not running, all searches fail (no fallback).
5. **Silent failures** — BM25 and title search catch exceptions and return empty lists without surfacing errors.
6. **No pagination** — Search always returns top `RERANK_TOP_N` (default 10); no cursor/offset support.
7. **No document detail page** — Result cards have no clickable destination.
8. **Frontend filter values hardcoded** — `["policy", "report", "deck", "memo"]` and `["pdf", "docx", "pptx"]` are static strings in `filter-panel.tsx`.
9. **Upload endpoint unprotected** — Anyone can upload documents without authentication.
10. **Zero tests** — No automated verification of any component.

---

## Recent Git History

```
06ba9c4  ui: frontend update (removing sign in)
f3a7b33  fix: now supporting pptx
90ab37f  feat: add title boosting and version-aware ranking to search pipeline
6393124  render to docx
e076dc7  Create Mini_Strategic_Plan.md
c2a885f  Upload first batch of auxiliary data
a44c30b  data: rename sample docs with clean descriptive titles
5c2c485  fix: sql and cors errors
032890b  data: ingestion fix
2a62303  local embedding model
2ddc459  infra: login page added
0c5348c  package: swapping to bun
6b6c03d  feat: implement complete MVP prototype
```

---

## Overall Maturity Assessment

| Area | Maturity |
|------|----------|
| Core search pipeline | Production-quality prototype |
| Document ingestion | Production-quality prototype |
| Frontend UI | Production-quality prototype |
| Version management | Complete |
| Docker deployment | Development-grade |
| Authentication | Implemented but not enforced |
| RBAC | Implemented but bypassed |
| Testing | None |
| Observability | None beyond stdout logs |
| Security hardening | Dev-only (hardcoded secrets, no rate limiting) |

**Bottom line:** The core value proposition (hybrid search with reranking over ingested documents) works end-to-end. Auth, RBAC, logging, tests, and production hardening are either bypassed or absent.
