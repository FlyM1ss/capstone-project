# AI-Driven Company-Wide Search Engine

An intelligent search engine prototype designed for enterprise document retrieval using hybrid search (semantic + keyword) powered by NLP and AI-driven reranking.

**Project**: ITWS 4100 IT Capstone | Deloitte  

---

## Project Overview

This system enables employees to search internal resources via natural language queries. It combines:

- **Semantic search** with dense vector embeddings (Qwen3-Embedding-0.6B, 1024-dimensional)
- **Keyword search** using BM25 (powered by ParadeDB)
- **Intelligent reranking** with Cohere Rerank v3.5
- **Role-based access control (RBAC)** with JWT authentication
- **Version-aware document tracking** with hybrid retrieval

### Key Features

- Natural language search across PDFs, Word docs, and PowerPoint presentations
- Hybrid search combining semantic + BM25 keyword matching
- Intelligent result reranking for improved relevance
- Document versioning with "latest-only", "all-versions", and "oldest-only" filters
- Role-based access control (analyst, manager, admin)
- Document upload and ingestion pipeline
- Full Docker Compose deployment
- Optional cloud-hosted embedding (Google Colab, Lambda, etc.)

---

## Technology Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Frontend** | Next.js 16 (App Router) + TypeScript | 16.x |
| **UI Framework** | shadcn/ui (@base-ui/react) | Latest |
| **Backend** | FastAPI | Python 3.11 |
| **Database** | PostgreSQL with ParadeDB (pgvector + BM25) | 16.x |
| **Embedding Model** | Qwen3-Embedding-0.6B | 1024-dim |
| **Reranker** | Cohere Rerank v3.5 | - |
| **Document Parser** | Docling | - |
| **Authentication** | JWT (HS256 + bcrypt) | - |
| **Orchestration** | Docker Compose | Latest |

---

## Quick Start

### Prerequisites

- **Docker** and **Docker Compose** (latest)
- **NVIDIA GPU** (optional; if unavailable, use [cloud-hosted embedding](docs/EMBEDDING_CLOUD_SETUP.md))
- **Python 3.11+** (for standalone backend development)
- **Node.js 18+** or **Bun** (for frontend development)

### Option 1: Full Stack with Docker Compose (Recommended)

#### 1. Clone and Configure

```bash
git clone <repo-url>
cd capstone-project
cp .env.example .env
```

Edit `.env` with your settings:

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/capstone
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Embedding
EMBEDDING_API_URL=http://embedding:8001/embed
# Or use cloud-hosted (see docs/EMBEDDING_CLOUD_SETUP.md):
# EMBEDDING_API_URL=https://your-colab-tunnel.trycloudflare.com/embed

# Reranking (optional, search degrades gracefully if empty)
COHERE_API_KEY=

# Auth
JWT_SECRET_KEY=your-secret-key-here-min-32-chars
NEXTAUTH_SECRET=your-nextauth-secret-here

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

#### 2. Start All Services

```bash
docker compose up -d
```

**On first run**, services will:
- Initialize the PostgreSQL database (`init.sql`)
- Download the embedding model (~600MB to GPU cache)
- Start all 4 services: `db`, `embedding`, `backend`, `frontend`

#### 3. Auto-Ingest Sample Data

After services are running, ingest documents:

```bash
docker compose exec backend python -m app.scripts.ingest_all
```

**Ingest options:**

```bash
# Re-ingest clean data (generic + auxiliary)
docker compose exec backend python -m app.scripts.ingest_all --clean

# Include adversarial data (malformed + prompt-injected + legacy poisoned)
docker compose exec backend python -m app.scripts.ingest_all --poisoned

# Everything
docker compose exec backend python -m app.scripts.ingest_all --all

# Specific categories or modes
docker compose exec backend python -m app.scripts.ingest_all --categories generic malformed
docker compose exec backend python -m app.scripts.ingest_all --mode malformed
docker compose exec backend python -m app.scripts.ingest_all --recursive --limit 25
```

Monitor ingestion progress:

```bash
docker compose logs -f backend
```

#### 4. Access the Application

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:3000 | Search interface |
| **Backend API** | http://localhost:8000 | API endpoints |
| **API Docs** | http://localhost:8000/docs | Swagger UI |
| **Database** | localhost:5432 | PostgreSQL (internal) |

#### 5. Demo Credentials

Use these accounts to test role-based access:

- **Admin** (all content): `admin@deloitte.com` / `password123`
- **Manager** (public + internal): `manager@deloitte.com` / `password123`
- **Analyst** (public only): `analyst@deloitte.com` / `password123`

---

### Option 2: Standalone Backend (Development)

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Requires a running PostgreSQL instance with `EMBEDDING_API_URL` set.

---

### Option 3: Standalone Frontend (Development)

```bash
cd frontend
bun install      # or: npm install
bun run dev      # Dev server on :3000
```

Configure `.env.local`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

### Option 4: Cloud-Hosted Embedding (No Local GPU)

For systems without an NVIDIA GPU, run the embedding server on **Google Colab** or similar:

See [Cloud-Hosted Embedding Setup Guide](docs/EMBEDDING_CLOUD_SETUP.md) for complete instructions.

Quick start:

```bash
# Set your cloud embedding URL in .env
EMBEDDING_API_URL=https://your-colab-tunnel.trycloudflare.com/embed

# Start stack without local embedding service
docker compose -f docker-compose.yml -f docker-compose.external-embedding.yml up -d
```

---

## Documentation

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](CLAUDE.md) | Detailed architecture, commands, and conventions |
| [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) | High-level design rationale |
| [Cloud Embedding Setup](docs/EMBEDDING_CLOUD_SETUP.md) | Google Colab embedding server guide |
| [Project Status](PROJECT_STATUS.md) | Current implementation status |
| [Testing Guide](docs/test-runs/2026-04-16-results.md) | Test results and validation |

---

## Common Commands

### Development

```bash
# Start full stack
docker compose up -d

# View logs
docker compose logs -f backend
docker compose logs -f frontend

# Stop services
docker compose down

# Stop + wipe all data (fresh start)
docker compose down -v

# Rebuild images (after requirements.txt/package.json changes)
docker compose up -d --build
```

### API Testing

```bash
# Health check
curl http://localhost:8000/api/health

# Search documents
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly report"}'

# Upload document
curl -X POST http://localhost:8000/api/documents \
  -F "file=@path/to/file.pdf"
```

### Database

```bash
# Connect to PostgreSQL
docker compose exec db psql -U postgres -d capstone

# Common queries
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM document_chunks;
SELECT COUNT(*) FROM query_logs;
```

### Frontend

```bash
cd frontend

# Development server
bun run dev

# Production build
bun run build

# Linting
bun run lint

# Type checking
bun run type-check
```

### Backend

```bash
cd backend

# Run tests (when available)
pytest tests/

# Format code
black app/

# Type check
mypy app/

# Lint
ruff check app/
```

---

## Architecture Overview

```
┌─────────────────────────────────────────┐
│          Frontend (Next.js)             │
│  Search UI + Upload + Admin Panel       │
└────────────────┬────────────────────────┘
                 │
         NEXT_PUBLIC_API_URL
                 │
┌────────────────▼────────────────────────┐
│       Backend (FastAPI)                 │
│  ┌──────────────────────────────────┐   │
│  │ Search Pipeline                  │   │
│  │ • Embedding Generation           │   │
│  │ • Semantic Search (pgvector)     │   │
│  │ • BM25 Keyword Search (ParadeDB) │   │
│  │ • Title Similarity               │   │
│  │ • RRF Merge                      │   │
│  │ • Cohere Reranking               │   │
│  │ • Version Filtering              │   │
│  │ • RBAC Filtering                 │   │
│  └──────────────────────────────────┘   │
└────────────────┬────────────────────────┘
                 │
        ┌────────┴────────┬──────────────┐
        │                 │              │
        ▼                 ▼              ▼
  ┌─────────────┐  ┌──────────────┐  ┌──────────────┐
  │ PostgreSQL  │  │  Embedding   │  │    Cohere    │
  │  (ParadeDB) │  │  Service     │  │   Reranker   │
  │             │  │              │  │              │
  │ • Vector DB │  │  Qwen3 0.6B  │  │  (Optional)  │
  │ • BM25 Index│  │  1024-dim    │  │              │
  │ • Metadata  │  │              │  │              │
  └─────────────┘  └──────────────┘  └──────────────┘
```

---

## Security

- **Authentication**: JWT tokens (HS256) with bcrypt password hashing
- **Authorization**: Role-based access control (analyst, manager, admin)
- **API**: All endpoints require valid JWT token
- **Secrets**: Never commit `.env` files; use `.env.example` as template
- **Database**: Credentials rotated in production

---

## Search Pipeline

1. **Query Embedding** → Generate 1024-dimensional vector using Qwen3
2. **Parallel Retrieval** →
   - Semantic search: pgvector cosine similarity on chunks (HNSW index)
   - BM25 search: ParadeDB keyword matching on chunks
   - Title search: pgvector cosine similarity on document titles (separate HNSW index)
3. **RRF Merge** → Combine 3 ranked lists using Reciprocal Rank Fusion (title-weighted)
4. **Reranking** → Cohere Rerank v3.5 (gracefully degrades if API unavailable)
5. **Filtering** →
   - Version filtering (latest-only, all-versions, oldest-only)
   - RBAC filtering (by access_level and user role)
6. **Return Results** → Top-K documents grouped by document

---

## Docker Services

| Service | Port | Purpose | Notes |
|---------|------|---------|-------|
| `frontend` | 3000 | Next.js dev server | Bun-based, mounts `src/` |
| `backend` | 8000 | FastAPI server | Auto-ingests on first start |
| `db` | 5432 | PostgreSQL + ParadeDB | Runs `init.sql`, persists to `pgdata` volume |
| `embedding` | 8001 | Embedding server | GPU-accelerated (CUDA), ~600MB model cache |

---

## Data Flow: Document Upload to Search

```
Upload (PDF/DOCX/PPTX)
    ↓
Docling Parser (extract text, tables, images)
    ↓
Text Chunking (512 tokens, 50-token overlap)
    ↓
Embedding Generation (Qwen3 1024-dim vectors)
    ↓
Database Storage
    ├─ document (metadata)
    ├─ document_chunks (text + embedding)
    ├─ document_title_embeddings (title vector)
    └─ BM25 Index (ParadeDB)
    ↓
Ready for Search
```

---

## Performance Tuning

Key parameters in `backend/app/core/config.py`:

```python
SEARCH_TOP_K = 50         # Top-K chunks to retrieve per search method
RERANK_TOP_N = 10         # Top-N to return after reranking
RRF_K = 60                # RRF parameter (larger = more weight on top ranks)
CHUNK_SIZE = 512          # Tokens per chunk
CHUNK_OVERLAP = 50        # Overlap between chunks
TITLE_BOOST_WEIGHT = 1.5  # Title match weight in RRF
EMBED_BATCH_SIZE = 64     # Batch size for embedding generation
```

---

## Troubleshooting

### Embedding service fails to start

**Problem**: "CUDA not available" or GPU memory exhausted

**Solution**: Use [cloud-hosted embedding](docs/EMBEDDING_CLOUD_SETUP.md) instead:

```bash
docker compose -f docker-compose.yml -f docker-compose.external-embedding.yml up -d
```

### Database connection errors

**Problem**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
docker compose down -v
docker compose up -d
sleep 5  # Wait for DB to initialize
docker compose exec backend python -m app.scripts.ingest_all
```

**Note (stale DB image / data)**: If the database appears to be running a stale image or old persistent data (for example after schema changes or when the DB seems out-of-date), stop and remove containers and volumes with `docker compose down -v` to force a fresh initialization. This removes named volumes (deleting stored DB data), so back up any important data before running it.

### Search returns no results

**Problem**: Documents not ingested or BM25 index not created

**Solution**:
```bash
docker compose exec backend python -m app.scripts.ingest_all --clean
docker compose logs -f backend
```

### "Token expired" on frontend

**Problem**: JWT token has expired (60-minute expiry)

**Solution**: Clear browser cookies or re-login. In production, implement refresh tokens.

---

## Monitoring

### Backend Health

```bash
curl http://localhost:8000/api/health
```

### Database Queries

```bash
docker compose exec db psql -U postgres -d capstone -c "SELECT COUNT(*) FROM documents;"
```

### Embedding Service

```bash
curl http://localhost:8001/health
# or: curl https://your-cloud-url/health
```

---

## Testing

See [Testing Guide](docs/search-agent-edge-case-test-pack.md) for:
- Search accuracy metrics
- Edge case handling
- Adversarial input validation
- Performance benchmarks

---

## License

Capstone project for Deloitte. Internal use only.

---

## Team

**Project**: ITWS 4100 Capstone  
**Institution**: Rensselaer Polytechnic Institute

---

## Support

For issues, questions, or feature requests:
- Review [CLAUDE.md](CLAUDE.md) for technical details
- Check [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) for architectural choices
- See [Cloud Embedding Setup](docs/EMBEDDING_CLOUD_SETUP.md) for GPU-less deployment

---

**Last Updated**: April 2026
