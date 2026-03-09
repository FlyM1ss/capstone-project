# Prototype MVP Design — Deloitte AI Search Engine

**Date:** 2026-03-09
**Scope:** Demo-ready MVP (Option B)
**Target:** Deliverable D4 — Functioning web application prototype

---

## Architecture Overview

Monorepo with Docker Compose. Three containers (frontend, backend, db) plus Colab-hosted embedding model.

```
capstone-project/
├── frontend/                # Next.js 15 (App Router)
│   ├── app/                 # Routes, layouts, pages
│   ├── components/          # UI components (shadcn/ui)
│   ├── lib/                 # Utilities, API client
│   ├── Dockerfile
│   └── package.json
├── backend/                 # FastAPI
│   ├── app/
│   │   ├── api/             # Route handlers
│   │   ├── core/            # Config, security, deps
│   │   ├── models/          # Pydantic schemas + DB models
│   │   ├── services/        # Search, NLP, ingestion, reranking
│   │   └── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── data/                    # Demo documents (gitignored)
│   └── sample-docs/         # Curated PDFs
├── docker-compose.yml       # PostgreSQL + backend + frontend
├── .env.example             # Template for secrets
└── software-engineering/    # Existing deliverables (untouched)
```

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Next.js 15 + TypeScript + shadcn/ui + Vercel AI SDK | Search UI, results, filters, admin upload |
| Backend | FastAPI + Uvicorn (Python 3.11+) | REST API, search orchestration, ingestion |
| Search | pgvector (semantic) + ParadeDB (BM25) + RRF merge | Hybrid retrieval from unified PostgreSQL |
| Reranking | Cohere Rerank 4 API | Cross-encoder reranking top 50 → top 10 |
| Embeddings | Qwen3-Embedding-0.6B on Google Colab (configurable) | 1024-dim vectors, ~50ms on GPU |
| Doc Processing | Docling | PDF parsing with table extraction |
| Auth | NextAuth.js + PostgreSQL roles | Simple RBAC (analyst/manager/admin) |
| Database | PostgreSQL 16 + pgvector + ParadeDB | Documents, chunks, users, query logs |
| Deployment | Docker Compose (3 containers + Colab) | frontend, backend, db |
| Demo Data | ~30-50 curated public PDFs | Consulting reports, policies, financials |

## Frontend Pages

| Page | Purpose |
|------|---------|
| `/` | Landing — search bar with info button for tips, example queries |
| `/search?q=...` | Results — filter panel left, ranked result cards center |
| `/documents/[id]` | Document detail — metadata + content preview |
| `/admin/upload` | Admin portal — drag-and-drop PDF upload, ingestion progress, document list |

Search tips: info button (i) inside search bar → expands collapsible panel with example queries and tips.

## Backend API Endpoints

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/search` | Hybrid search with filters |
| GET | `/api/documents` | List ingested documents |
| POST | `/api/documents` | Upload + ingest PDFs |
| GET | `/api/documents/{id}` | Get document detail |
| GET | `/api/health` | Health check |

## Search Pipeline

1. `POST /api/search {query, filters}` → validate input
2. Classify intent + generate embedding (Qwen3 endpoint)
3. **Parallel:** pgvector cosine similarity (top 50) + ParadeDB BM25 (top 50)
4. Reciprocal Rank Fusion merge → top 50 candidates
5. Cohere Rerank 4 → top 10 results
6. Apply role-based access filtering (WHERE access_level check)
7. Return results, log query asynchronously

## Ingestion Pipeline

1. Admin uploads PDF(s) via `/admin/upload`
2. Backend receives at `POST /api/documents`
3. Docling extracts structured text (preserves tables)
4. Chunker splits into ~512-token chunks with 50-token overlap
5. Each chunk embedded via Qwen3 endpoint (Colab or local CPU fallback)
6. Parent `documents` row + `document_chunks` rows stored in PostgreSQL

## Database Schema

```sql
documents (
    id              UUID PRIMARY KEY,
    title           TEXT NOT NULL,
    author          TEXT,
    doc_type        TEXT,              -- 'pdf', 'docx', 'pptx'
    category        TEXT,              -- 'policy', 'report', 'deck', 'memo'
    created_date    TIMESTAMPTZ,
    access_level    TEXT DEFAULT 'public',  -- 'public', 'internal', 'confidential'
    file_path       TEXT,
    page_count      INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

document_chunks (
    id              UUID PRIMARY KEY,
    document_id     UUID REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER,
    content         TEXT NOT NULL,
    embedding       VECTOR(1024),
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

users (
    id              UUID PRIMARY KEY,
    email           TEXT UNIQUE NOT NULL,
    name            TEXT,
    role            TEXT DEFAULT 'analyst',  -- 'analyst', 'manager', 'admin'
    created_at      TIMESTAMPTZ DEFAULT NOW()
)

query_logs (
    id              UUID PRIMARY KEY,
    user_id         UUID REFERENCES users(id),
    query_text      TEXT,
    result_count    INTEGER,
    selected_doc_id UUID,
    latency_ms      INTEGER,
    created_at      TIMESTAMPTZ DEFAULT NOW()
)
```

## Auth Model

- NextAuth.js with credentials provider (email/password for demo)
- User roles stored in `users.role` column in PostgreSQL
- Middleware checks role before returning search results
- Three roles: `analyst` (public docs), `manager` (public + internal), `admin` (all + upload access)

## Embedding Model Deployment

- **Primary:** Google Colab notebook with Qwen3-Embedding-0.6B + ngrok tunnel
- **Fallback:** CPU inference in backend container via sentence-transformers
- Backend reads `EMBEDDING_API_URL` from `.env` — swappable without code changes

## Demo Data

~30-50 curated public PDFs simulating Deloitte internal resources:
- Public consulting reports (Deloitte, McKinsey, BCG)
- Generic HR/travel/expense policy templates
- Financial reports with tables and charts (SEC filings, annual reports)
- Short slide-deck-style PDFs (5-10 pages)

## Dropped from MVP

- Keycloak (replaced by NextAuth.js standalone)
- Semantic caching
- "Did you mean?" suggestions
- Multilingual support
- Mobile-native views
