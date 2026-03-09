# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ITWS 4100 (IT Capstone) project — an AI-driven company-wide search engine prototype for Deloitte. The system uses NLP with hybrid retrieval (semantic + BM25 keyword search) to let employees search internal resources via natural language queries.

**Tech stack:** Next.js 15 (App Router) + TypeScript + shadcn/ui + Vercel AI SDK frontend, FastAPI backend, PostgreSQL 16 with pgvector + ParadeDB (unified hybrid search), Qwen3-Embedding-0.6B embeddings, Cohere Rerank v3.5, Docling (document parsing), NextAuth.js (auth), Docker Compose deployment.

## Repository Structure

- `frontend/` — Next.js 15 App Router frontend
  - `app/` — Pages: landing (`/`), search results (`/search`), admin upload (`/admin/upload`)
  - `components/` — UI components (search-bar, result-card, filter-panel, file-upload) + shadcn/ui
  - `lib/api.ts` — API client for backend communication
- `backend/` — FastAPI backend
  - `app/api/` — Route handlers (health, auth, documents, search)
  - `app/services/` — Business logic (search, ingestion, embeddings, reranker, auth, validation)
  - `app/models/` — SQLAlchemy ORM models (`db.py`) and Pydantic schemas (`schemas.py`)
  - `app/core/` — Config, database connection, dependency injection
  - `app/scripts/ingest_all.py` — Batch document ingestion script
  - `db/init.sql` — Database schema with pgvector + ParadeDB setup
- `docker-compose.yml` — 3 containers: db (ParadeDB), backend, frontend
- `notebooks/` — Colab embedding server setup instructions
- `scripts/` — Demo data download script
- `software-engineering/` — Software design deliverable (docx/gdoc generation, Mermaid diagrams)
- `docs/plans/` — Architecture design and implementation plans
- `Proposal/`, `Pre-Project-Research/`, `CostBenefitAnalysis/` — Project deliverables

## Key Commands

```bash
# Start all services
docker compose up -d

# Check backend health
curl http://localhost:8000/api/health

# Upload a document
curl -X POST http://localhost:8000/api/documents -F "file=@path/to/file.pdf"

# Search
curl -X POST http://localhost:8000/api/search -H "Content-Type: application/json" -d '{"query": "quarterly report"}'

# Batch ingest demo documents
docker compose exec backend python -m app.scripts.ingest_all

# Frontend dev (standalone)
cd frontend && npm run dev

# Generate the software engineering .docx
cd software-engineering && python3 build_docx.py
```

## Secrets

- `.env` (root) — Database creds, Cohere API key, NextAuth secret, embedding URL. Copy from `.env.example`.
- `credentials.json` / `token.json` (in `software-engineering/`) — Google OAuth, gitignored.
- Never commit `.env`, API keys, or credential files.

## Architecture Notes

- **Search pipeline**: Query → embed (Qwen3) → parallel pgvector cosine + ParadeDB BM25 → RRF merge → Cohere rerank → RBAC filter → results
- **Embedding model**: Hosted on Google Colab with ngrok tunnel, backend reads `EMBEDDING_API_URL` from `.env`
- **Database**: Single PostgreSQL (ParadeDB image) provides both vector search and BM25 — no separate vector DB
- **Auth**: JWT tokens with 3 roles — analyst (public docs), manager (+internal), admin (+confidential, +upload)
- **Demo users**: admin@deloitte.com / manager@deloitte.com / analyst@deloitte.com (password: "password123")

## Conventions

- Monorepo: frontend and backend are sibling directories, orchestrated by Docker Compose
- Backend follows layered architecture: `api/` → `services/` → `models/` → database
- Frontend uses Next.js App Router with `"use client"` directives for interactive components
- Diagram source of truth is `.mmd` files in `software-engineering/diagrams/`
