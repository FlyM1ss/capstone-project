# Capstone Project - Complete Current Status Report

- **Generated:** 2026-04-28
- **Repository checkout:** `main` at `ffdb0b1` (`Revert "feat: summarize from search results"`)
- **Scope:** Accurate status for the current local working tree. `origin/main` is visible and ahead, but not checked out.

---

## Executive Status

The project is a functional academic prototype for AI-driven enterprise document search. The core backend pipeline is implemented: document ingestion, parsing, chunking, embedding, hybrid retrieval, RRF fusion, optional Cohere reranking, version filtering, document preview, and cached document-detail summaries.

The frontend is also functional for the main user workflow: search, filter by file type/date, view result snippets, pin documents, track recents, open a document detail page, preview/download the source file, inspect extracted text, and request an AI summary.

The system is not production-ready. Auth exists but is not enforced, upload and document endpoints are open, query logging is schema-only, the frontend has no login flow, there are no automated tests, and the Docker stack is development/demo oriented.

---

## Current Tech Stack

| Area | Current implementation |
| --- | --- |
| Frontend | Next.js 16.2.3, React 19.2.4, React Router DOM 7.14.0, TypeScript, SCSS modules, npm, Node 20 Docker image |
| Backend | FastAPI 0.115.12, Python 3.11, async SQLAlchemy 2.0.41, asyncpg |
| Database | ParadeDB PostgreSQL with pgvector and pg_search |
| Embeddings | Qwen3-Embedding-0.6B, 1024-dimensional vectors, served by local Docker/standalone FastAPI embedding service |
| Reranking | Cohere Rerank v3.5, optional fallback to RRF order |
| Summaries | Cohere Chat `command-r-08-2024`, cached on document rows |
| Parsing | Docling 2.31.0 for PDF/DOCX/PPTX |
| Preview conversion | Gotenberg 8 for DOCX/PPTX to PDF conversion |
| Auth primitives | JWT HS256, bcrypt/passlib, seeded users; not enforced in primary workflows |
| Deployment | Docker Compose dev/demo stack with GPU embedding service and CPU override |

---

## Directory Structure

```text
capstone-project/
+-- backend/
|   +-- app/
|   |   +-- api/                    # FastAPI routers: health, auth, documents, search
|   |   +-- core/                   # settings, async DB engine/session, DI re-export
|   |   +-- models/                 # SQLAlchemy ORM + Pydantic schemas
|   |   +-- scripts/                # ingest_all.py batch ingestion CLI
|   |   +-- services/               # search, ingestion, embeddings, rerank, auth, summaries, PDF conversion
|   |   +-- main.py                 # app setup, CORS, exception handlers, router mounts
|   +-- db/init.sql                 # schema, indexes, demo users
|   +-- tests/                      # stub only
|   +-- Dockerfile
|   +-- requirements.txt
+-- frontend/
|   +-- src/
|   |   +-- pages/                  # Next Pages Router catch-all and app shell
|   |   +-- App.tsx                 # React Router route tree
|   |   +-- pages-views/            # Search, results, account, document detail views
|   |   +-- components/             # UI components
|   |   +-- context/                # user, theme, documents/pins/recents
|   |   +-- api/                    # backend API client wrappers
|   |   +-- types/
|   +-- Dockerfile                  # node:20-alpine, npm ci, npm run dev
|   +-- package.json
+-- data/
|   +-- generic/
|   +-- auxiliary/
|   +-- malformed/
|   +-- prompt-injected/
|   +-- poisoned/
|   +-- sample/
|   +-- sample-docs/
+-- docs/
|   +-- search-agent-edge-case-test-pack.md
|   +-- test-runs/
|   +-- superpowers/
+-- coursework/
+-- docker-compose.yml
+-- docker-compose.cpu.yml
+-- embedding_server.py
+-- embedding.Dockerfile
+-- embedding.cpu.Dockerfile
+-- DESIGN_DECISIONS.md
+-- PROJECT_STATUS.md
```

---

## Backend Status

| Component | Status | Notes |
| --- | --- | --- |
| FastAPI app | Complete | Routers mounted under `/api`; CORS is permissive for demo. |
| Health check | Complete | `GET /api/health` checks DB connectivity. |
| Auth login | Partial | `POST /api/auth/login` issues JWTs, but frontend and protected endpoints do not use them. |
| JWT helpers | Partial | bcrypt and HS256 implemented; secret is hardcoded. |
| Document upload | Complete but unprotected | `POST /api/documents`; accepts PDF/DOCX/PPTX by extension and ingests immediately. |
| Document list/detail | Complete but unprotected | `GET /api/documents`, `GET /api/documents/{id}`. |
| Raw file download | Complete but unprotected | `GET /api/documents/{id}/file`. |
| PDF preview | Complete but unprotected | `GET /api/documents/{id}/preview`; PDFs returned directly, DOCX/PPTX converted through Gotenberg. |
| Extracted chunks | Complete but unprotected | `GET /api/documents/{id}/chunks`. |
| AI summary | Complete but optional/unprotected | `GET /api/documents/{id}/summary`; requires Cohere key and caches results in DB. |
| Query validation | Partial | Length checks and four prompt-injection/XSS-like regex patterns. |
| Docling parsing | Complete | PDF/DOCX/PPTX to markdown-like text. |
| Chunking | Complete | Word-based, 512 words, 50-word overlap. |
| Embedding client | Complete | Batched HTTP calls to embedding service, 503 on unavailable service. |
| Content hash skip | Complete | Unchanged `(document_group, version)` files are skipped. |
| Title embeddings | Complete | Separate table and HNSW index. |
| BM25 index | Complete | Lazy creation after chunks exist. |
| Hybrid retrieval | Complete | Semantic chunks + BM25 + title similarity. |
| RRF merge | Complete | `RRF_K=60`, title boost `1.5`. |
| Cohere rerank | Complete/optional | Falls back to RRF ordering when unavailable. |
| Latest-version filter | Complete | Enabled by frontend for all searches. |
| RBAC filtering | Designed but bypassed | Search endpoint hardcodes admin role. |
| Query logging | Schema only | `query_logs` table exists; no writes. |
| Tests | Not implemented | No pytest or backend test suite. |

---

## Frontend Status

| Component | Status | Notes |
| --- | --- | --- |
| Next.js host | Complete | Pages Router catch-all dynamically imports the app with SSR disabled. |
| React Router routes | Complete | `/`, `/results`, `/account`, `/document/:id`. |
| Search landing page | Complete | Greeting, search bar, filters. |
| Results page | Complete | Calls backend search, caches responses in memory, shows service errors. |
| Result item | Complete | Links to document page, snippet, metadata, pin button. |
| Document detail page | Complete | Preview/text tabs, download, metadata, AI summary side panel. |
| Account page | Demo only | Displays static demo admin user. |
| Sidebar | Complete | Pinned and recent documents. |
| Theme support | Complete | Dark/light mode via localStorage and `data-theme`. |
| Pins/recents | Complete | localStorage scoped by demo user id. |
| Search response cache | Complete | In-memory max 20 search requests. |
| File type filters | Complete | Sent to backend as comma-separated `doc_type`. |
| Date range filter | Partial | Applied client-side after search results return. |
| Access/authorized filter | Broken/partial | Frontend sends `access_level`, but backend search ignores that filter and runs as admin. |
| Admin upload UI | Not implemented | Backend upload route exists, but no frontend upload page exists in this checkout. |
| Login/session UI | Not implemented | Frontend uses static demo user and sends no bearer tokens. |
| Search-result summaries | Not implemented by current HEAD | Added in `3fea768`, reverted in `ffdb0b1`; detail-page summaries remain. |

---

## Infrastructure Status

| Component | Status | Notes |
| --- | --- | --- |
| Docker Compose | Complete for dev/demo | Defines DB, embedding, backend, Gotenberg, frontend. |
| DB container | Complete | ParadeDB image, init SQL, health check. |
| Embedding container | Complete | GPU image with NVIDIA reservation and health check. |
| CPU embedding override | Complete | `docker-compose.cpu.yml` swaps in CPU image and removes GPU reservations. |
| Backend container | Complete | Python 3.11 slim, hot reload, data mount. |
| Gotenberg container | Complete | Internal conversion service for previews. |
| Frontend container | Complete | Node 20, npm install, dev server. |
| `.env.example` | Partial | Lists common vars, but Docker backend needs `EMBEDDING_API_URL=http://embedding:8001/embed`; NextAuth vars are stale. |
| Auto-ingestion | Not implemented | Backend logs document count at startup; run `ingest_all` manually. |
| Production deployment | Not implemented | No TLS, secrets manager, migrations, CI, backups, scaling, or observability. |

---

## API Endpoints

| Method | Path | Runtime auth | Status |
| --- | --- | --- | --- |
| `GET` | `/api/health` | None | Complete |
| `POST` | `/api/auth/login` | None | Complete JWT issuance |
| `POST` | `/api/search` | Hardcoded admin | Functional, RBAC bypassed |
| `GET` | `/api/documents` | None | Complete |
| `POST` | `/api/documents` | None | Complete ingestion, unprotected |
| `GET` | `/api/documents/{id}` | None | Complete |
| `GET` | `/api/documents/{id}/file` | None | Complete |
| `GET` | `/api/documents/{id}/preview` | None | Complete with Gotenberg for DOCX/PPTX |
| `GET` | `/api/documents/{id}/chunks` | None | Complete |
| `GET` | `/api/documents/{id}/summary` | None | Complete if Cohere is configured |

---

## Search Pipeline

```text
Frontend query
  -> POST /api/search
  -> validate_query()
  -> generate query embedding with Qwen service
  -> pgvector semantic chunk search
  -> ParadeDB BM25 chunk search
  -> pgvector title embedding search
  -> weighted RRF merge
  -> optional Cohere rerank
  -> batch document metadata fetch
  -> collapse duplicate documents
  -> latest-version filter
  -> SearchResponse
```

Operational notes:

- `top_k` request field defaults to 10 and is bounded 1-50.
- Retrieval candidates use `SEARCH_TOP_K=50`.
- Reranking returns `RERANK_TOP_N=10` by default.
- Frontend always sends `show_latest_only: true`.
- Cohere rerank failure is silent fallback.
- BM25/title SQL failures roll back and continue, but are not logged.

---

## Database Schema

| Table | Purpose |
| --- | --- |
| `documents` | Metadata, access level, file path, versioning, content hash, cached summary. |
| `document_chunks` | Chunk text and 1024-dim embeddings. |
| `document_title_embeddings` | One title embedding per document. |
| `users` | Demo users and roles. |
| `query_logs` | Designed for analytics/audit; unused. |

Important indexes:

- HNSW on `document_chunks.embedding`.
- HNSW on `document_title_embeddings.embedding`.
- B-tree indexes on chunk document id, document access level, category, document group, query log user id.
- BM25 `idx_chunks_bm25` created lazily after ingestion.

---

## Data Corpus Status

Tracked data files total: 100.

| Folder | Count | Purpose |
| --- | ---: | --- |
| `data/generic` | 6 | Broad enterprise appendix documents. |
| `data/auxiliary` | 52 | Clean curated policies, standards, reports, and decks. |
| `data/malformed` | 6 | Parser robustness and malformed-file testing. |
| `data/prompt-injected` | 6 | Prompt-injection style adversarial content. |
| `data/poisoned` | 24 | Legacy poisoned/conflicting corpus. |
| `data/sample` | 4 | Older sample documents. |
| `data/sample-docs` | 2 | Legacy external sample PDFs. |

Default clean ingest:

```bash
docker compose exec backend python -m app.scripts.ingest_all
```

Useful variants:

```bash
docker compose exec backend python -m app.scripts.ingest_all --poisoned
docker compose exec backend python -m app.scripts.ingest_all --all
docker compose exec backend python -m app.scripts.ingest_all --clean
docker compose exec backend python -m app.scripts.ingest_all --mode prompt-injected
docker compose exec backend python -m app.scripts.ingest_all --categories generic malformed
docker compose exec backend python -m app.scripts.ingest_all --recursive --limit 25
```

---

## Key Configuration

From `backend/app/core/config.py`:

```python
DATABASE_URL = "postgresql+asyncpg://deloitte:deloitte_dev@localhost:5432/search_engine"
EMBEDDING_API_URL = "http://localhost:8001/embed"
COHERE_API_KEY = ""
GOTENBERG_URL = "http://localhost:3001"
SEARCH_TOP_K = 50
RERANK_TOP_N = 10
RRF_K = 60
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
TITLE_BOOST_WEIGHT = 1.5
EMBED_BATCH_SIZE = 64
```

Docker-specific values are passed through Compose/environment. In Docker, backend should call the embedding service at `http://embedding:8001/embed`; standalone backend can use `http://localhost:8001/embed`.

---

## Known Gaps and Risks

| Area | Gap | Impact |
| --- | --- | --- |
| Auth enforcement | Search hardcodes `user_role = "admin"` | RBAC is bypassed. |
| Frontend auth | Static demo user, no login/token handling | JWT login endpoint is unused by UI. |
| Upload security | Upload endpoint is unauthenticated | Any caller can ingest documents. |
| Document access | File/preview/chunks/summary endpoints are unauthenticated | Any caller with document id can read content. |
| JWT secret | Hardcoded secret in source | Tokens can be forged by anyone with code access. |
| Frontend access filter | Sends unsupported `access_level` filter | UI filter does not reliably affect backend results. |
| Query logging | No inserts into `query_logs` | No analytics or audit trail. |
| Tests | No automated backend/frontend tests | No regression safety. |
| Migrations | No Alembic/migration flow | Schema updates require resets/manual SQL. |
| Upload validation | Extension-only, no size/MIME scan | Unsafe for untrusted uploads. |
| CORS | Wildcard origins with credentials | Not production safe. |
| Rate limiting | None | Login/search/upload can be abused. |
| Observability | Minimal logs, no metrics/tracing | Hard to diagnose production issues. |
| Deployment | Dev Compose only | No production hardening. |

---

## Git and Worktree Status

Observed before documentation edits:

- Local branch: `main`.
- Local HEAD: `ffdb0b1 Revert "feat: summarize from search results"`.
- Remote HEAD: `origin/main` at `710be02 Update .gitignore`.
- Branch relationship: local `main` is ahead 1 and behind 34.
- Existing untracked files before this work: `AGENTS.md` and `frontend/.dockerignore`.

Notable current-history commits:

```text
ffdb0b1 Revert "feat: summarize from search results"
3fea768 feat: summarize from search results
6d51da9 feat: ai summary
da5d5dc feat: add PPTX/DOCX preview via Gotenberg PDF conversion
6603889 chore: rename Fetch/ to frontend/, consolidate coursework into coursework/
c49ad1b Merge pull request #6 from FlyM1ss/feat/document-preview-and-pins
a90799c feat: add CPU-only Docker profile for non-NVIDIA environments
e96da3b Add finalized auxiliary documents
90ab37f feat: add title boosting and version-aware ranking to search pipeline
6b6c03d feat: implement complete MVP prototype
```

Remote-only commits visible after local HEAD mostly relate to final report polish and follow-up fixes. They should be merged or rebased before treating this checkout as synchronized with GitHub.

---

## Test Coverage

Automated coverage is effectively 0%.

- `backend/tests/` has no actual tests.
- Frontend `package.json` has no test script.
- No CI configuration was found in the reviewed files.
- Manual/recorded testing exists in `docs/test-runs/2026-04-16-results.md` and `docs/search-agent-edge-case-test-pack.md`.

Recommended first automated tests:

1. Unit tests for `_extract_version_info()`, `_sanitize_bm25_query()`, and `_filter_latest_versions()`.
2. API tests for `/api/search` error behavior when embedding service is unavailable.
3. Ingestion tests for unchanged hash skip and changed same-version replacement.
4. Frontend API mapping tests for `search.ts` filter conversion.
5. Integration test for document detail endpoints using a seeded PDF.

---

## Overall Maturity

| Area | Maturity |
| --- | --- |
| Core search pipeline | Strong prototype |
| Document ingestion | Strong prototype |
| Document preview/download | Functional prototype |
| AI summaries | Functional optional feature |
| Frontend search/detail UX | Functional prototype |
| Docker local stack | Functional development/demo setup |
| Auth/RBAC | Designed but not enforced |
| Security hardening | Demo-only |
| Testing | Missing |
| Observability | Minimal |
| Production readiness | Not ready |

Bottom line: the project is complete enough for a capstone demo of AI-powered enterprise search, document preview, and summary-assisted triage. The next engineering phase should focus on auth enforcement, frontend/backend filter correctness, tests, migrations, and operational hardening.
