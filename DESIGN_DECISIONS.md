# DELOITTE AI SEARCH ENGINE — MAJOR SOFTWARE DESIGN DECISIONS

**Project Timeline:** 33 commits spanning March 2026 (initial concept → current state)
**Deliverable Context:** ITWS 4100 IT & WEB SCIENCE CAPSTONE — Prototype enterprise search engine
**Author Analysis Date:** 2026-03-25

---

## EXECUTIVE SUMMARY

This document catalogs major architectural and technology choices in a hybrid semantic + keyword search system for enterprise documents. The project prioritizes **demo functionality** over long-term scalability, yielding several deliberate tradeoffs: external embedding service, unified PostgreSQL database, permissive auth defaults, and careful document versioning via filename convention.

---

## 1. DATABASE ARCHITECTURE

### 1.1 PostgreSQL 16 + pgvector + ParadeDB (vs. Elasticsearch, Pinecone, Weaviate)

**Decision:** Single PostgreSQL instance (ParadeDB fork) handling both vector search and keyword search.

**Evidence:**
- **Files:** `docker-compose.yml` (`image: paradedb/paradedb:latest`), `backend/db/init.sql`
- **Config:** `backend/app/core/config.py` (`DATABASE_URL` single endpoint)

**Context/Timing:** Established at MVP inception (March 9, 2026). Indicates preference for minimal operational complexity for a capstone project.

**Tradeoffs:**

| Aspect | PostgreSQL (ParadeDB) | Elasticsearch | Pinecone |
|--------|---|---|---|
| **Setup** | One container, single URL | Separate cluster, config complexity | Cloud-only (no local dev) |
| **Vector + keyword in one DB** | Yes (pgvector + pg_search) | Yes (vector search plugin) | Separate indices |
| **Cost for capstone demo** | Free, open-source | License + ops overhead | SaaS, per-vector pricing |
| **Query complexity** | Raw SQL (lower abstraction) | Query DSL learning curve | Proprietary API |
| **Semantic search quality** | pgvector HNSW (competitive) | Lucene-based (proven) | Pinecone reranking |
| **Admin/demo convenience** | Full SQL access, `psql` CLI | REST API + Kibana | Dashboard only |

**Why not alternatives:**
- **Elasticsearch:** Over-engineered for a 50-doc demo; license complexity; requires separate vector indices until recent versions
- **Pinecone / Weaviate:** Cloud dependency kills offline dev iteration; pricing per vector; less control over tuning parameters
- **Qdrant / Milvus:** Operational overhead; complexity for demo timeline
- **Column stores (DuckDB, Clickhouse):** Not specialized for hybrid search; lack mature vector plugins

---

### 1.2 Separate `document_title_embeddings` Table (vs. Single `document_chunks` Table)

**Decision:** Title embeddings stored in dedicated table with independent HNSW index.

**Evidence:**
- **Commit:** `90ab37f` ("feat: add title boosting and version-aware ranking")
- **Files:** `backend/db/init.sql`, `backend/app/models/db.py`

**Rationale:** Keeps `documents` clean as a metadata table — no 1024-dim vector bloating every row fetch. HNSW index lives on a compact, dedicated table — faster index builds (tens of rows vs thousands of chunks). Independently tunable: can swap embedding model, dimensions, or index strategy for titles without touching chunk infrastructure.

**Context/Timing:** Mid-project enhancement (March 19, 2026). Added after MVP skeleton but before final polish.

**Tradeoffs:**
- **Pro:** Cleaner schema separation; title-only searches extremely fast; future model swaps isolated
- **Con:** Two embedding calls per document (title + chunks); cascade deletes; slightly more ingestion logic

---

## 2. SEARCH PIPELINE

### 2.1 Hybrid Search: Semantic + BM25 + Title Boosting (vs. Pure Vector, Pure Keyword, or AI-Only)

**Decision:** Three parallel retrieval paths (cosine similarity on chunks, ParadeDB BM25 on chunks, cosine similarity on titles) merged with Reciprocal Rank Fusion.

**Evidence:**
- **Commits:** `6b6c03d` (initial) + `90ab37f` (title addition)
- **File:** `backend/app/services/search.py` (`hybrid_search` function)

**Pipeline flow:**
```
1. generate_embedding(query)                              [§4.1: external embedding]
2. Parallel: semantic (pgvector), BM25 (ParadeDB), title search (pgvector)
3. RRF merge (3 lists, title_weight=1.5)                 [§2.2: merging strategy]
4. Batch document metadata fetch (fixes N+1)
5. Cohere rerank (top 50 → top 10)                       [§4.3: reranking decision]
6. Version filter (show_latest_only)                     [§5: document versioning]
7. Return results
```

**Why three signals instead of alternatives:**

| Approach | Reason for Rejection |
|----------|----------------------|
| **Pure semantic (vector-only)** | Breaks on domain jargon ("Q3 report" vs. "Q3_Business_Review.pptx" filename); no lexical match for acronyms |
| **Pure keyword (BM25 only)** | Misses semantic paraphrasing ("employee benefits" should match "compensation packages"); no document title preference |
| **AI-only (LLM chain)** | Requires API calls per query; latency + cost; no clear improvement for retrieval task |
| **Title-only boost in BM25** | Title boost within one search loses signal independence; RRF lets each signal contribute equally then weight |

**Context/Timing:**
- MVP foundation (March 9): Semantic + BM25 baked into initial design
- Enhancement (March 19): Title signal added when users observed title match importance

**Tradeoffs:**
- **Pro:** Robust ranking; leverages multiple signals; title match explicit; adjustable via `TITLE_BOOST_WEIGHT`
- **Con:** Three database queries per search; complex RRF logic; tuning three signals (K values, weight)

---

### 2.2 Reciprocal Rank Fusion (RRF) Merging

**Decision:** Standard RRF formula with title-weighted variant.

**Evidence:**
- **File:** `backend/app/services/search.py` (`_rrf_merge` function)
- **Config:** `backend/app/core/config.py` (`RRF_K=60`, `TITLE_BOOST_WEIGHT=1.5`)

**RRF formula:**
```python
rrf_score += 1.0 / (k + rank + 1)
```
where k=60 (tuning parameter).

**Title boosting:** Title matches scored independently; all chunks from a title-matched document get boost: `score += title_weight * (1.0 / (k + title_rank + 1))`.

**Why RRF over alternatives:**

| Method | Reason for Choice |
|--------|-------------------|
| **RRF** | Rank-agnostic; handles lists of different lengths; no normalizing by magnitude; proven in IR literature |
| **Linear combination** | Requires normalizing 3 score types to [0,1]; semantic cosine ~0.2-0.9, BM25 unbounded — normalization adds fragility |
| **Learned ranking** | No training data; no time for LambdaMART / LTR pipeline |

**Tuning parameters:**
- `RRF_K=60`: Large K favors diversity; smaller K would favor top results more aggressively
- `TITLE_BOOST_WEIGHT=1.5`: Multiplier only; flexible adjustment without reindexing

---

## 3. DOCUMENT INGESTION & PARSING

### 3.1 Docling for Document Parsing (vs. PyPDF2, pdfplumber, LlamaParse)

**Decision:** Docling library as single parser for PDF, DOCX, PPTX.

**Evidence:**
- **File:** `backend/requirements.txt` (`docling==2.31.0`)
- **Usage:** `backend/app/services/ingestion.py` (`DocumentConverter`, `_parse_document`)
- **Multi-format support added:** Commit `f3a7b33` ("fix: now supporting pptx")

**Format support:**
```python
allowed_formats=[
    InputFormat.PDF,
    InputFormat.DOCX,
    InputFormat.PPTX,
],
```

**Why Docling:**

| Feature | Docling | PyPDF2 | pdfplumber | LlamaParse |
|---------|---------|--------|-----------|-----------|
| **PDF parsing** | Yes (table-aware) | Yes (basic) | Yes (precise) | Yes (LLM-powered) |
| **DOCX support** | Yes (native) | No | No | Yes |
| **PPTX support** | Yes | No | No | Via image extraction |
| **Table extraction** | Structured markdown | Raw text | Cell-level | LLM summaries |
| **Cost** | Free, open-source | Free | Free | SaaS API, per-page pricing |
| **Format output** | Markdown (consistent) | Raw strings | JSON | LLM-generated |

**Why not LlamaParse:** Cost-prohibitive for demo; requires API key + internet; introduces LLM latency.

**Chunking strategy** (`backend/app/services/ingestion.py`):
```python
def chunk_text(text_content: str, chunk_size: int = 512, overlap: int = 50):
    words = text_content.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap
```

**Config** (`backend/app/core/config.py`): `CHUNK_SIZE=512, CHUNK_OVERLAP=50`

**Chunking choice rationale:**
- **512 words ≈ 1500–2000 tokens** (reasonable for 1024-dim embedding model context)
- **50-word overlap:** ~10% — balances semantic continuity with chunk count inflation
- **Word-level (not token-level):** Simpler; avoids tokenizer dependency; slight inefficiency acceptable for demo

**Tradeoffs:**
- **Pro:** Single library handles 3 formats; table extraction; free; consistent output (markdown)
- **Con:** Slower than PyPDF2; requires OCR for scanned PDFs

---

### 3.2 Version Detection from Filename Convention

**Decision:** Extract `document_group` and `version` from filename pattern `*_v(\d+)`.

**Evidence:**
- **Commit:** `90ab37f` ("feat: add title boosting and version-aware ranking")
- **File:** `backend/app/services/ingestion.py` (`_extract_version_info`)

**Pattern matching:**
```python
def _extract_version_info(filename: str) -> tuple[str, int]:
    stem = Path(filename).stem
    match = re.search(r'_v(\d+)$', stem)
    if match:
        version = int(match.group(1))
        base = stem[:match.start()]
    else:
        version = 1
        base = stem
    document_group = base.replace("_", " ").replace("-", " ").strip().lower()
    return document_group, version
```

**Examples:**
- `Remote_Work_Policy_v2.docx` → group=`"remote work policy"`, version=`2`
- `Acceptable_Use_Policy.pdf` → group=`"acceptable use policy"`, version=`1`

**Why filename convention instead of metadata or uploader choice:**
- No XMP/properties metadata in typical enterprise PDFs
- Reduces upload friction; deterministic
- Naming convention already familiar to developers (v1, v2, etc.)
- Non-versioned files default to v1 (no breakage)

**Database constraint:** `UNIQUE (document_group, version)` prevents duplicate versions.

**Limitation:** Requires naming discipline; no rollback mechanism; detection happens once at ingestion.

---

## 4. EMBEDDING & RERANKING

### 4.1 External Embedding Service: Qwen3-Embedding-0.6B on Google Colab (vs. Local, OpenAI, Cohere)

**Decision:** HTTP client calling remote embedding endpoint (default: `http://localhost:8001/embed`).

**Evidence:**
- **File:** `backend/app/services/embeddings.py`
- **Config:** `backend/app/core/config.py` (`EMBEDDING_API_URL`)
- **Docker:** `docker-compose.yml` (`EMBEDDING_API_URL=${EMBEDDING_API_URL:-http://host.docker.internal:8001/embed}`)

**Endpoint contract:**
```python
async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.EMBEDDING_API_URL,
            json={"texts": texts},
        )
        return response.json()["embeddings"]
```

**Why Qwen3-Embedding-0.6B on Colab:**

| Choice | Rationale |
|--------|-----------|
| **Qwen3-Embedding-0.6B** | 1024-dim vectors (rich representation); reasonable latency on GPU; permissive license; no quota |
| **External (Colab)** | No GPU in capstone environment; keeps backend CPU-light; swappable via env var |
| **HTTP API** | Loose coupling; easy to swap models; local fallback feasible |

**Why not alternatives:**

| Option | Reason for Rejection |
|--------|----------------------|
| **OpenAI embeddings** | API cost per vector; external dependency; lock-in |
| **Cohere embeddings** | SaaS dependency; pricing; 1024-dim costs more than smaller models |
| **Sentence-transformers (local)** | Requires GPU in backend container OR slow CPU inference; adds image complexity |
| **ONNX local model** | Inference latency on CPU; storage overhead; complexity |

**Deployment context:**
- **Primary:** Google Colab + ngrok tunnel
- **Fallback:** Local `embedding_server.py` in root directory
- **Docker:** Points to `host.docker.internal:8001` (macOS/Windows); needs override for Linux

**Context/Timing:**
- Core decision at MVP inception (March 9)
- Local server option formalized mid-project (March 12) for offline development

---

### 4.2 Cohere Rerank v3.5 for Cross-Encoder Reranking

**Decision:** Optional Cohere API for reranking top 50 candidates → top 10.

**Evidence:**
- **File:** `backend/app/services/reranker.py`
- **Config:** `backend/app/core/config.py` (`COHERE_API_KEY`)

**Reranker code:**
```python
async def rerank_results(query: str, texts: list[str], top_n: int = 10) -> list[int]:
    if not settings.COHERE_API_KEY or not texts:
        return list(range(min(top_n, len(texts))))
    try:
        co = cohere.Client(settings.COHERE_API_KEY)
        response = co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=texts,
            top_n=top_n,
        )
        return [r.index for r in response.results]
    except Exception:
        return list(range(min(top_n, len(texts))))  # Graceful fallback
```

**Fallback behavior:** If API key missing or call fails, returns original RRF ranking.

**Why Cohere Rerank (vs. alternatives):**

| Approach | Rationale |
|----------|----------------------|
| **Cohere Rerank v3.5** | Fast (~tens of ms); competitive accuracy; graceful degradation; API-swappable |
| **No reranking** | RRF provides decent initial ranking; reranking adds latency; optional for demo |
| **Local cross-encoder** | Would need model in backend; GPU slowdown; more dependencies to manage |

**Config tuning:**
- `RERANK_TOP_N=10`: Retrieve top 50, rerank to 10
- Justification: Cohere cost grows with doc count; 10 results reasonable for search UX

---

## 5. DOCUMENT VERSIONING & DEDUPLICATION

### 5.1 Version-Aware Filtering: `document_group` + `version` + Show Latest Only Toggle

**Decision:** Link versions via `document_group`, detect version from filename, provide frontend toggle to filter post-rank.

**Evidence:**
- **Commit:** `90ab37f` ("feat: add title boosting and version-aware ranking")
- **Files:** `backend/db/init.sql`, `backend/app/services/search.py` (`_filter_latest_versions`), `frontend/lib/api.ts`

**Filtering logic:**
```python
def _filter_latest_versions(results: list[SearchResultItem]) -> list[SearchResultItem]:
    latest_versions: dict[str, int] = {}
    for r in results:
        if r.document_group is None or r.version is None:
            continue
        if r.document_group not in latest_versions or r.version > latest_versions[r.document_group]:
            latest_versions[r.document_group] = r.version

    return [
        r for r in results
        if r.document_group is None
        or r.version is None
        or r.version == latest_versions.get(r.document_group)
    ]
```

**Why post-rank filtering (not pre-rank or indexing strategy):**
- Rank first, filter later: user might explicitly want older versions
- Simpler query: avoids complex GROUP BY logic
- Flexible toggle: user-controlled without re-executing search

**Limitations:**
- No version rollback; unique constraint means overwriting loses old row
- Manual naming discipline required
- No granular version browser in UI (toggle only)

---

## 6. AUTHENTICATION & AUTHORIZATION

### 6.1 JWT + Role-Based Access Control (vs. Session-based, OAuth, Attribute-based)

**Decision:** JWT tokens (HS256, 60-minute expiry) with role column in users table; search endpoint hardcodes `user_role = "admin"` for demo.

**Evidence:**
- **File:** `backend/app/services/auth.py`
- **Database:** `backend/db/init.sql` (`users` table with `role` column)
- **Search endpoint:** `backend/app/api/search.py` (`user_role = "admin"  # permissive for demo`)

**Role model:**
```sql
role TEXT DEFAULT 'analyst' CHECK (role IN ('analyst', 'manager', 'admin')),
```

**Demo roles:**
| Role | Access Level |
|------|--------------|
| `analyst` | Public docs only |
| `manager` | Public + internal |
| `admin` | Public + internal + confidential + upload |

**RBAC filter:**
```python
def _get_access_levels(role: str) -> list[str]:
    if role == "admin":
        return ["public", "internal", "confidential"]
    elif role == "manager":
        return ["public", "internal"]
    return ["public"]
```

**Why JWT:**

| Choice | Rationale |
|--------|-----------|
| **JWT** | Stateless; scales horizontally; standard; works with FastAPI DI; no server-side session storage |
| **Session-based** | Requires Redis/Memcached; cross-site issues; less API-friendly |
| **OAuth 2.0** | Appropriate for delegation; adds complexity; requires external IdP |
| **ABAC** | Overkill for 3-level role hierarchy; policy engine complexity |

**Why NOT enforced in demo:**
- Full auth integration with frontend not prioritized for MVP
- Capstone focus is search quality, not security
- All users see all results; easier testing/demonstration

**Credentials seeded** (`db/init.sql`):
- `admin@deloitte.com`, `manager@deloitte.com`, `analyst@deloitte.com` — password: `password123`

---

## 7. BACKEND FRAMEWORK CHOICE

### 7.1 FastAPI (vs. Django, Flask, Express, Actix)

**Decision:** FastAPI with Uvicorn for backend REST API.

**Evidence:**
- **File:** `backend/requirements.txt` (`fastapi==0.115.12`, `uvicorn[standard]==0.34.2`)
- **Main app:** `backend/app/main.py` (FastAPI app with CORS middleware + 4 routers)

**Why FastAPI:**

| Feature | FastAPI | Django | Flask | Express (Node.js) |
|---------|---------|--------|-------|-------------------|
| **Type hints** | Native (Pydantic auto-validates) | Django ORM types | Manual validation | Optional (TS helps) |
| **Async support** | First-class (async/await everywhere) | Django 3.1+ partial; complex | Limited | Native |
| **API documentation** | Auto-generated OpenAPI + Swagger | Manual or add-ons | Manual | Manual |
| **PostgreSQL fit** | SQLAlchemy async excellent | Django ORM excellent | SQLAlchemy adequate | Sequelize/Prisma |

**Why not Django:** Over-engineered for REST-only API; startup overhead; better suited for full-stack monolith.

**Why not Flask:** Under-featured; lacks built-in async support; requires many extensions.

**CORS configuration** (`main.py`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
Permissive for demo (not production-safe); allows frontend on different port to call backend.

---

## 8. FRONTEND FRAMEWORK & BUILD TOOLING

### 8.1 Next.js 15 (App Router) vs. React SPA, Remix, SvelteKit

**Decision:** Next.js 15 with App Router (not Pages Router), TypeScript, shadcn/ui components.

**Evidence:**
- **File:** `frontend/package.json`
- **Architecture:** `frontend/app/` directory structure (App Router)
- **Components:** shadcn/ui imports throughout UI components

**Why Next.js 15 App Router:**

| Feature | Next.js (App) | React SPA | Remix | SvelteKit |
|---------|-------|-----------|-------|-----------|
| **SSR/SSG** | Native | Not built-in | Built-in | Built-in |
| **File-based routing** | Yes | Manual (React Router) | Yes | Yes |
| **TypeScript** | First-class | Manual setup | Excellent | Excellent |
| **Community** | Very large (Vercel-backed) | Massive | Growing | Niche |
| **Deployment** | Vercel native | Netlify/others | Remix cloud | SvelteKit cloud |

**App Router vs. Pages Router:**
- Next.js 15 App Router stabilized 2024; natural choice for 2026 project
- Pages Router is legacy, being phased out

**UI component library: shadcn/ui** (not Material-UI, Chakra, Headless UI)
- Built on Radix UI + Tailwind CSS 4
- Copy-paste components (no npm dependency lock-in)
- Full customization; minimal magic

---

### 8.2 Bun Package Manager (vs. npm, yarn, pnpm)

**Decision:** Switched from npm to Bun for frontend package management.

**Evidence:**
- **Commit:** `0c5348c` ("package: swapping to bun")
- **File:** `frontend/Dockerfile` (`FROM oven/bun:1-alpine`, `RUN bun install`)

**Why Bun:**

| Metric | Bun | npm | yarn | pnpm |
|--------|-----|-----|------|------|
| **Speed** | ~3-5x faster (Rust-based, parallel) | Baseline | ~2x faster | ~2x faster |
| **Disk space** | Efficient (hardlinks) | Default (full copies) | Efficient | Very efficient |
| **Docker image** | oven/bun (50MB) | node (200MB) | node (200MB) | node (200MB) |
| **Compatibility** | 100% npm packages | 100% | ~95% | ~98% |

**Why chosen:**
- Faster dev iteration (`bun run dev` vs. `npm run dev`)
- Leaner Docker image (`oven/bun:1-alpine` vs. `node:20-alpine`)
- Demonstrates awareness of modern tooling
- No compatibility downside; fully npm-compatible

---

## 9. DEPLOYMENT & ORCHESTRATION

### 9.1 Docker Compose (vs. Kubernetes, Serverless, Manual VMs)

**Decision:** Single `docker-compose.yml` with 3 services (PostgreSQL, FastAPI backend, Next.js frontend).

**Evidence:**
- **Commit:** `6b6c03d` (initial MVP with full docker-compose)
- **File:** `docker-compose.yml` (3 services + 2 volumes)

**Services:**
```yaml
services:
  db:      # paradedb/paradedb:latest — port 5432, volume-mounted init.sql
  backend: # ./backend — port 8000, hot reload via volume mount
  frontend:# ./frontend — port 3000, hot reload via volume mount
```

**Why Docker Compose:**

| Choice | Rationale |
|--------|-----------|
| **Docker Compose** | Single yaml file; zero extra tooling; works offline; all-in-one |
| **Kubernetes** | Overkill for 3 containers; cluster overhead (Minikube/Kind); 10+ yaml files |
| **Serverless (Vercel/Lambda)** | Backend less natural (cold starts, stateless requirement); separate DB hosting |
| **Manual VMs** | More DevOps burden; harder to reproduce environment |

**Docker Compose fit for capstone:**
- **One-command startup:** `docker compose up -d`
- **Volume mounts:** Hot reload for dev (`./backend:/app`, `./frontend:/app`)
- **Health checks:** `depends_on: condition: service_healthy` ensures DB ready before backend

**Limitations:**
- Not production-grade; no auto-scaling, rolling updates, or secrets management
- Single-host only (no multi-node cluster)
- Volumes are host-local (not suitable for cloud without modification)

---

### 9.2 Environment Variable Management & Secrets

**Decision:** `.env` file (gitignored) with `.env.example` template; no hardcoded secrets.

**Evidence:**
- **Commit:** `13924cf` ("secret: database url hiding") — moved `DATABASE_URL` from docker-compose to `.env`
- **Files:** `.env.example`, `docker-compose.yml` (`${VAR:-default}` syntax)

**`.env` structure** (from `.env.example`):
```env
POSTGRES_USER=deloitte
POSTGRES_PASSWORD=deloitte_dev
DATABASE_URL=postgresql+asyncpg://deloitte:deloitte_dev@db:5432/search_engine
EMBEDDING_API_URL=http://localhost:8001/embed
COHERE_API_KEY=your_cohere_api_key_here
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXTAUTH_URL=http://localhost:3000
```

**Defaults in docker-compose.yml:** `${POSTGRES_USER:-deloitte}` — allows `.env` to be optional for demo.

**Limitations:**
- No encryption at rest
- No audit trail (HashiCorp Vault or k8s Secrets would provide this)
- Acceptable for capstone; not for production

---

## 10. SEARCH TUNING PARAMETERS

**Location:** `backend/app/core/config.py`

| Parameter | Value | Reasoning |
|-----------|-------|-----------|
| `SEARCH_TOP_K` | 50 | Retrieve 50 candidates from each of 3 sources before reranking |
| `RERANK_TOP_N` | 10 | Cohere Rerank limit; balance latency vs. accuracy (top 10 sufficient for search UX) |
| `RRF_K` | 60 | RRF constant; higher K = favor diversity; tuned empirically |
| `CHUNK_SIZE` | 512 | Words per chunk; ~1500–2000 tokens; fits embedding context window |
| `CHUNK_OVERLAP` | 50 | ~10% overlap; balances semantic continuity with chunk count inflation |
| `TITLE_BOOST_WEIGHT` | 1.5 | Multiplier in RRF for title matches; 1.5x preferred over strict 1.0 |

**Note:** All parameters hardcoded; production system would expose these via admin dashboard.

---

## 11. QUALITY ASSURANCE

### 11.1 Minimal Test Coverage (No Test Framework)

**Decision:** No automated testing framework in codebase.

**Evidence:**
- `backend/tests/` directory contains only `__init__.py` (empty)
- No test-related commits in git history
- No testing commands in CLAUDE.md

**Rationale:**
- Capstone scope: focus on functionality over robustness
- Rapid prototyping: manual curl/UI testing faster than unit test setup
- Deliverable is "functioning prototype," not "production-ready system"

**What was tested manually:**
- Search pipeline (example queries in `/docs/demo-queries.md`)
- Ingestion (batch ingest script: `backend/app/scripts/ingest_all.py`)
- API endpoints (curl examples in CLAUDE.md)

**Limitations:**
- No regression protection if code refactored
- Fragile to future changes (no safety net)

---

## 12. DATA ARCHITECTURE & INGESTION

### 12.1 Multi-Source Dataset: Sample Docs + Auxiliary Data + Poisoned Data

**Evidence:**
- **Commit:** `c2a885f` ("Upload first batch of auxiliary data") — 60+ curated documents
- **Commit:** `a44c30b` ("data: rename sample docs with clean descriptive titles")
- **Folder structure:** `data/sample-docs/`, `data/auxiliary/`, `data/poisoned/`

**Ingestion script options:**
```bash
python -m app.scripts.ingest_all              # Clean data only
python -m app.scripts.ingest_all --poisoned   # Adversarial test only
python -m app.scripts.ingest_all --all        # Everything
```

**Dataset composition:**
- **Sample docs:** ~7 curated PDFs (academic papers, consulting concepts)
- **Auxiliary:** ~60 corporate policies, reports, presentations (realistic Deloitte-like)
- **Poisoned:** ~30 intentionally misleading or conflicting documents (adversarial testing)

**Purpose of poisoned data:** Evaluate search pipeline robustness to conflicting information and adversarial inputs.

---

## DESIGN DECISION TIMELINE

| Phase | Commits | Key Decisions |
|-------|---------|---------------|
| **Concept** (March 1–8) | `41c3061` → `6b6c03d` | Overall architecture (Docker Compose, FastAPI, Next.js, PostgreSQL + pgvector + ParadeDB, hybrid search) |
| **MVP build** (March 9) | `6b6c03d` | Full-stack implementation, Docling, JWT auth, RBAC, Qwen3 embeddings, Cohere rerank |
| **Stabilization** (March 9–15) | `13924cf`, `0c5348c`, `2a62303` | Secrets management, Bun package manager, local embedding server, CORS |
| **Feature expansion** (March 19) | `90ab37f` | Title boosting, version-aware ranking, `document_group` deduplication |
| **Polish** (March 20–25) | Various | Data ingestion, BM25 sanitization, frontend auth removal (demo simplification) |

---

## ARCHITECTURAL PHILOSOPHY & TRADEOFFS

### Design Principles Observed

1. **Simplicity over sophistication:** Docker Compose over k8s; RRF over learned ranking; filename convention over metadata parsing
2. **External over embedded:** Embedding service out-of-process; Cohere reranking optional; loosely coupled via env vars
3. **Graceful degradation:** Missing Cohere key → fallback to RRF order; failed embedding call → logged; toggle defaults safe
4. **Demo-first, scalability-later:** Permissive CORS; hardcoded admin role in search; no rate limiting

### Scalability Hotspots (Not Addressed)

- **Embedding latency:** External service at 30s timeout; batch API calls mitigate but single point of failure
- **Database scale:** PostgreSQL fine for <100k documents; HNSW indexes efficient; BM25 untested at scale
- **Concurrent search:** No caching, no query deduplication; each query re-embeds the full query string
- **Versioning:** Filename convention fragile; no version rollback; overwrites lose old row permanently

### Reliability Gaps

- No automated testing (risk: untested refactorings break search)
- No observability/logging (difficult to debug production search quality issues)
- No alerting (if embedding service goes down, ingestion fails silently)
- No backup/recovery (database failure = data loss)

These gaps are acceptable for **capstone MVP**; would be critical blockers for production Deloitte deployment.

---

## 13. SECURITY DECISIONS

> **Overall assessment:** The codebase demonstrates solid foundational security practices (parameterized queries, bcrypt hashing, structured JWT) but carries intentional demo-first shortcuts (hardcoded admin role, permissive CORS, no rate limiting). Suitable for prototype/academic purposes; requires significant hardening before enterprise deployment.

---

### 13.1 Input Validation & Prompt Injection Defense

**Decision:** Pydantic schema-level validation + custom regex pattern matching for prompt injection.

**Evidence:**
- **File:** `backend/app/services/validation.py` — `validate_query()` function
- **File:** `backend/app/models/schemas.py` — `SearchRequest` model
- **Called from:** `backend/app/api/search.py`

**What was implemented:**

Pydantic model (`schemas.py`):
```python
query: str = Field(..., min_length=1, max_length=500)
top_k: int = Field(default=10, ge=1, le=50)
```

`validate_query()` service function:
```python
injection_patterns = [
    r"ignore\s+(all\s+)?previous\s+instructions",
    r"system\s*prompt",
    r"you\s+are\s+now",
    r"<\s*script",
]
for pattern in injection_patterns:
    if re.search(pattern, query, re.IGNORECASE):
        raise HTTPException(status_code=400, detail="Query contains disallowed patterns")
```

**Attack vector addressed:**
- **Prompt injection:** Blocks explicit override instructions directed at an LLM
- **XSS via query:** Blocks `<script` tags embedded in queries
- **Embedding DoS:** 500-char limit prevents overloading the external embedding server

**Why this approach over alternatives:**
- A small regex blocklist is sufficient here because **no LLM is in the search loop** — queries are embedded and matched, not interpreted. Sophisticated injections that don't match these patterns still produce normal document retrieval results.
- Pydantic schema validation is the first line of defense (runs before service code); regex patterns are a second layer for semantic patterns.
- A full ML classifier for injection detection would be overkill for a system with no instruction-following component.

**Known limitations:**
- Blocklist covers only 4 patterns; indirect injections (`"reveal all confidential documents"`) pass through (but are harmless — they become search queries, not instructions)
- Multilingual injection patterns not covered
- No PII detection in queries (email addresses, SSNs could be typed and later logged)
- No language detection / locale-based pattern expansion
- **Commit when introduced:** `6b6c03d` (MVP); `90ab37f` (query sanitization hardened)

---

### 13.2 BM25 Query Sanitization (Tantivy Operator Injection Defense)

**Decision:** Strip Tantivy query parser special characters before BM25 search.

**Evidence:**
- **File:** `backend/app/services/search.py` — `_sanitize_bm25_query()` function

**What was implemented:**
```python
def _sanitize_bm25_query(query: str) -> str:
    sanitized = re.sub(r"[+\-&|!(){}\[\]^\"~*?:\\/']", " ", query)
    return " ".join(sanitized.split())
```
Strips 18 special characters used by the Tantivy query engine (underlying ParadeDB BM25).

**Attack vector addressed:**
- **BM25 operator injection:** Prevents users from embedding Tantivy operators like `content:password*` (wildcard field search), `title AND NOT body:...` (boolean logic), or `"exact phrase"` (phrase matching) that could produce unexpected result sets or parser crashes.
- **Denial of service via malformed queries:** Tantivy parser errors on syntactically invalid queries; this prevents those errors from bubbling up.

**Why strip over reject:**
- Characters are silently stripped rather than causing an error, so legitimate queries containing punctuation (e.g., `C++`, `"quarterly report"`) still work, just without the operator semantics.
- Tradeoff: users don't know their query was modified. A proper solution would validate in `validation.py` and reject.

**Commit when introduced:** `90ab37f` — added mid-project after testing revealed BM25 parse errors on certain punctuation-heavy queries.

---

### 13.3 SQL Injection Protections

**Decision:** Parameterized queries (SQLAlchemy `text()` with bind params) for all raw SQL; ORM for all user/document CRUD.

**Evidence:**
- **File:** `backend/app/services/search.py` — all three search SQL blocks
- **File:** `backend/app/services/auth.py` — `select(User).where(User.email == email)`

**What was implemented:**
```python
# All dynamic values bound as parameters, never interpolated
semantic_sql = text(f"""
    SELECT ... WHERE d.access_level IN ({access_placeholders})
""")
result = await db.execute(semantic_sql, {"embedding": ..., **access_params})
```

Dynamic SQL structure (e.g., `IN (:access_0, :access_1)`) is built with static Python; values are always bound parameters.

**Attack vector addressed:**
- **SQL injection via query filters, access level, category, doc_type:** User-controlled values passed as named parameters, never string-interpolated into SQL
- **Second-order injection:** ORM-based user lookup prevents crafted email strings from becoming SQL

**Why not full ORM for search:**
- pgvector's `<=>` cosine operator and ParadeDB's `paradedb.score()` are not expressible in SQLAlchemy's ORM query builder — raw SQL is necessary
- Parameterized `text()` provides equivalent injection safety to ORM for the values that matter

**Commit when introduced:** `6b6c03d` (MVP) — consistent from initial implementation.

---

### 13.4 Password Hashing

**Decision:** bcrypt via `passlib` for all stored passwords.

**Evidence:**
- **File:** `backend/app/services/auth.py`
- **Dependency:** `backend/requirements.txt` (`passlib[bcrypt]==1.7.4`)

**What was implemented:**
```python
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

**Attack vector addressed:**
- **Offline brute force / rainbow tables:** bcrypt is memory-hard with adaptive cost factor (`$2b$12$` = 4096 rounds); attacker can't pre-compute hashes
- **Password reuse attack:** bcrypt auto-generates a unique salt per hash

**Why bcrypt over alternatives:**
| Algorithm | Reason for/against |
|-----------|-------------------|
| **bcrypt** | Proven, widely-used; passlib handles salt+cost automatically; `deprecated="auto"` future-proofs |
| **Argon2** | More modern; marginally better; would be preferred for greenfield but bcrypt is entirely sufficient |
| **SHA-256/MD5** | Not acceptable (fast hashes; brute-forceable) |
| **PBKDF2** | Acceptable but less commonly used in Python ecosystem |

**Known limitation:** All demo users share the same hash (same weak password `password123`), which is not a security issue per se (bcrypt hashes are salted) but reflects demo-data practices.

**Commit when introduced:** `6b6c03d` (MVP).

---

### 13.5 JWT Token Architecture

**Decision:** HS256 JWT tokens with 60-minute expiry; role embedded as claim.

**Evidence:**
- **File:** `backend/app/services/auth.py`
- **Dependency:** `backend/requirements.txt` (`python-jose[cryptography]==3.4.0`)

**What was implemented:**
```python
SECRET_KEY = "dev-secret-key-change-in-production"  # ← CRITICAL GAP
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
```

**Attack vector addressed:**
- **Session hijacking:** Short 60-minute expiry limits window if token is intercepted
- **Token forgery:** HS256 HMAC signature prevents crafting valid tokens without the secret

**Critical gap — Hardcoded secret key:**
- `SECRET_KEY = "dev-secret-key-change-in-production"` is committed to source code
- An attacker with code access can forge any JWT
- Should be loaded from environment: `settings.JWT_SECRET_KEY`
- **Not listed as a required `.env` variable** in `.env.example`

**Second critical gap — Token never validated in search:**
- `backend/app/api/search.py` line 21: `user_role = "admin"  # permissive for demo`
- JWT is issued by `/api/auth/login` but **never decoded** by the search endpoint
- This renders the entire auth system effectively bypassed for search

**Why JWT over sessions:**
- Stateless: no server-side session store (Redis) needed
- Standard: works with FastAPI dependency injection
- Mobile/API friendly: no cookie coupling

**Commit when introduced:** `6b6c03d` (MVP). The bypass was also present from day one, per design.

---

### 13.6 RBAC Design

**Decision:** Three-tier role hierarchy (`analyst` → `manager` → `admin`) stored in users table; enforced via access level filter in search SQL.

**Evidence:**
- **File:** `backend/db/init.sql` — `role` column with CHECK constraint
- **File:** `backend/app/services/search.py` — `_get_access_levels()`

**What was designed:**
```python
def _get_access_levels(role: str) -> list[str]:
    if role == "admin":
        return ["public", "internal", "confidential"]
    elif role == "manager":
        return ["public", "internal"]
    return ["public"]
```

SQL enforces access level at query time:
```sql
WHERE d.access_level IN (:access_0, :access_1, ...)
```

**Attack vector addressed (when enforced):**
- **Privilege escalation via search:** Analysts can't see confidential documents
- **Data exfiltration:** Role filter is applied server-side in SQL, not client-side

**Why three tiers:**
- Mirrors Deloitte's likely org structure (analysts, managers, admins)
- Simple enough to implement quickly; attribute-based access control (ABAC) would require a policy engine
- CHECK constraint on `access_level` prevents invalid classification levels being inserted

**Status: Architecture is designed correctly but currently bypassed.** The bypass (`user_role = "admin"` hardcode) makes this dead code at runtime.

**Gap — No auth on document upload:**
- `POST /api/documents` has no `Depends(get_current_user)` or role check
- Anyone can upload documents regardless of role
- The `admin` role was intended to be the only one with upload permission (per schema design)

**Commit when introduced:** `6b6c03d` (MVP).

---

### 13.7 CORS Policy

**Decision:** Permissive wildcard CORS (`allow_origins=["*"]`) for demo.

**Evidence:**
- **File:** `backend/app/main.py` — `CORSMiddleware` configuration
- **Commit:** `6b6c03d` (set at MVP); documented as demo trade-off

**What was implemented:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Why this was chosen:**
- Allows frontend (`localhost:3000`) to call backend (`localhost:8000`) without a reverse proxy
- Simplifies local development (no nginx needed)
- Demo environment with no real secrets means CSRF risk is academic

**Attack vector this creates:**
- **CSRF:** Any website can make credentialed requests to the backend from a logged-in user's browser
- **Data exfiltration via third-party site:** Malicious site could trigger searches and read responses

**Why it's acceptable for demo:** No real user data; auth is bypassed anyway; no production traffic.

**Production fix:** Restrict to specific frontend domain; remove `allow_credentials=True` unless cookies are used.

---

### 13.8 Secrets Management

**Decision:** `.env` file (gitignored) + `.env.example` template; Docker Compose uses `${VAR:-default}` substitution.

**Evidence:**
- **Commit:** `13924cf` ("secret: database url hiding") — moved `DATABASE_URL` out of `docker-compose.yml`
- **Files:** `.env.example`, `.gitignore`, `docker-compose.yml`

**What was implemented:**
- `.env` is gitignored; never committed
- `.env.example` checked in as a template
- Docker Compose pulls from env: `${COHERE_API_KEY}`, `${NEXTAUTH_SECRET}`, etc.

**Why this approach:**
- Standard `dotenv` pattern; supported natively by docker-compose and Next.js
- Lightweight; no additional tooling required
- Reduces accidental secret commits (only template is committed)

**Known gaps:**
1. **JWT secret is hardcoded in Python**, not in `.env` (see §13.5)
2. **Database defaults are visible in source:** `${POSTGRES_PASSWORD:-deloitte_dev}` — fallback is in `docker-compose.yml`
3. **No secrets rotation mechanism** — Cohere key or DB password compromised requires manual replacement and redeploy
4. **No encryption at rest** — `.env` is plaintext on the developer's machine

**Production approach:** HashiCorp Vault, AWS Secrets Manager, or GCP Secret Manager for production secrets; CI/CD injects secrets at deploy time.

---

### 13.9 File Upload Security

**Decision:** Extension-based file type check; no MIME validation, size limits, or upload authentication.

**Evidence:**
- **File:** `backend/app/api/documents.py`
- **Ingestion:** `backend/app/services/ingestion.py`

**What was implemented:**
```python
if not file.filename.lower().endswith((".pdf", ".docx", ".pptx")):
    raise HTTPException(status_code=400, detail="Only PDF, DOCX, PPTX files are supported")
```

**Attack vector addressed:**
- **Unsupported format errors:** Prevents Docling from attempting to parse Excel, ZIP, etc.

**Gaps (intentional for demo):**
| Gap | Risk |
|----|------|
| Extension-only check (not MIME or magic bytes) | `malware.exe` renamed to `malware.pdf` would pass |
| No file size limit | 1GB upload could exhaust memory during Docling parsing |
| No auth on upload endpoint | Anyone can upload documents |
| No antivirus/malware scan | Malicious PDFs reach Docling parser untested |
| No sandbox for parsing | Docling parser runs in main backend process |

**Why gaps are acceptable for demo:** Upload is a controlled admin operation in demo context; no external users; Docling is trusted library.

**Production fix:** Add MIME type validation (`python-magic`), set `MAX_UPLOAD_SIZE`, add `Depends(require_admin)`, wrap Docling in a subprocess with timeout.

---

### 13.10 Audit Logging

**Decision:** Designed `query_logs` table in schema; not implemented in application code.

**Evidence:**
- **File:** `backend/db/init.sql` — `query_logs` table definition
- **No evidence:** No INSERT into `query_logs` anywhere in `backend/app/`

**Schema designed:**
```sql
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    query_text TEXT,
    result_count INTEGER,
    selected_doc_id UUID,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**Attack vector / compliance requirement addressed (when implemented):**
- **Insider threat detection:** Query logs reveal unusual access patterns (e.g., analyst querying confidential terms repeatedly)
- **Compliance:** Audit trails required for SOC 2, ISO 27001 — what data was accessed, by whom, when
- **Forensics:** Post-breach investigation requires knowing which documents were retrieved

**Why not implemented yet:**
- Time constraint; demo doesn't require compliance
- Without auth enforcement, `user_id` would always be null (pointless logging)

**Status: Gap.** Table exists, no code writes to it.

**Production fix:** Add post-search logging middleware that records `user_id`, `query_text` (possibly redacted for PII), `result_count`, `latency_ms` to `query_logs`.

---

### 13.11 Error Handling & Information Disclosure

**Decision:** Silent exception handling in search fallbacks; generic error messages in auth.

**Evidence:**
- **File:** `backend/app/services/search.py` — `try/except Exception` blocks around BM25 and title search
- **File:** `backend/app/api/auth.py` — `"Invalid email or password"` message

**Strengths:**
- Auth endpoint returns `"Invalid email or password"` without distinguishing between unknown email and wrong password — prevents email enumeration
- Search fallbacks avoid leaking stack traces to users

**Gaps:**
- Silent exceptions in search (`except Exception: pass`) suppress errors without logging — bugs are hidden, not just from users but from developers too
- No structured logging (`logger.error(...)`) means failed BM25 searches produce no signal

**Production fix:** Catch exceptions, log them with structured context (`logger.error(..., exc_info=True)`), still return graceful response to user.

---

### 13.12 Security Headers (Not Implemented)

**Status: Gap.** No HTTP security headers are set anywhere in the stack.

**Missing headers and their purpose:**

| Header | Protects Against |
|--------|-----------------|
| `X-Frame-Options: DENY` | Clickjacking — prevents search UI from being embedded in a malicious iframe |
| `Content-Security-Policy` | XSS — restricts which scripts/resources the browser will execute |
| `X-Content-Type-Options: nosniff` | MIME sniffing — prevents browser from executing mis-labelled content |
| `Strict-Transport-Security` | SSL stripping — forces HTTPS in production |
| `Referrer-Policy` | Referrer leakage — controls what URL is sent to third parties |

**Why not implemented:** Demo runs over HTTP locally; security headers are a production concern.

**Production fix:** Add a security headers middleware to FastAPI; configure Next.js `headers()` in `next.config.js`.

---

### Security Decision Summary

| Category | Implementation | Severity of Gap | Status |
|----------|---------------|-----------------|--------|
| Input validation (Pydantic) | Implemented | None | Complete |
| Prompt injection regex blocklist | Implemented (4 patterns) | Low (no LLM in loop) | Partial |
| BM25 operator sanitization | Implemented | Low | Complete |
| SQL injection (parameterized queries) | Implemented | None | Complete |
| Password hashing (bcrypt) | Implemented | None | Complete |
| JWT token issuance | Implemented | Medium (hardcoded key) | Partial |
| JWT token validation in search | NOT ENFORCED | Critical | Gap (intentional) |
| RBAC access level filtering | Designed, bypassed | Critical | Gap (intentional) |
| Auth on document upload | NOT IMPLEMENTED | High | Gap |
| CORS policy | Permissive wildcard | Critical (for production) | Intentional demo |
| Secrets in `.env` (gitignored) | Implemented | Low | Complete |
| JWT secret from env | NOT IMPLEMENTED | Critical | Gap |
| Rate limiting | NOT IMPLEMENTED | Critical | Gap |
| Audit logging (query_logs) | Schema only, no writes | High | Gap |
| File upload MIME validation | NOT IMPLEMENTED | Medium | Gap |
| File upload size limit | NOT IMPLEMENTED | Medium | Gap |
| HTTP security headers | NOT IMPLEMENTED | Medium | Gap |
| Error handling / no leakage | Partial (silent catches) | Medium | Partial |

**Critical gaps for production (in priority order):**
1. Enforce JWT validation in search endpoint + remove `user_role = "admin"` hardcode
2. Load `JWT_SECRET_KEY` from environment (add to `.env.example`)
3. Implement rate limiting on `/api/auth/login` and `/api/search`
4. Implement audit logging (write to `query_logs` table)
5. Add `Depends(require_admin)` to document upload endpoint
6. Restrict CORS to frontend domain

---

## CONCLUSION

This codebase represents a **pragmatic, timeline-constrained prototype** that prioritizes **feature completion over operational maturity**. Major decisions cluster around:

1. **Technology fit:** FastAPI, Next.js 15, PostgreSQL (ParadeDB) are modern, well-adopted choices with good async/typing support
2. **Search quality:** Hybrid semantic + BM25 + title boosting is a solid foundation; RRF merging is simple but effective
3. **Deployment simplicity:** Docker Compose scales to demo environments; one-command startup critical for capstone demo day
4. **User experience:** Title boosting and version filtering address real ranking gaps discovered during development
5. **Graceful degradation:** Optional reranking, fallback auth, error handling allow system to remain functional under partial failures

**For production Deloitte deployment**, prioritized improvements would be:
- Automated testing (regression safety)
- Observability (logging, tracing, metrics)
- Scalable embedding infrastructure (batch processing, caching, local GPU)
- Enforced RBAC (remove `user_role = "admin"` hardcode)
- Encryption and secrets management (HashiCorp Vault)
- Kubernetes orchestration (multi-region, auto-scaling)
- Query analytics and relevance feedback loop
