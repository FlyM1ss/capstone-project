# Deloitte AI Search Engine - Architecture Decisions

- **Project:** ITWS 4100 IT & Web Science Capstone - Deloitte prototype
- **Updated:** 2026-04-28
- **Scope:** Current checked-out working tree at `main` / `ffdb0b1` (`Revert "feat: summarize from search results"`). `origin/main` is ahead of this checkout; this document describes the files actually present locally.

## Current System Shape

The project is a monorepo with:

- `backend/`: FastAPI API, async SQLAlchemy, document ingestion, hybrid retrieval, reranking, document preview, summaries, auth primitives.
- `frontend/`: Next.js 16 Pages Router catch-all page that disables SSR and mounts a React Router SPA.
- `data/`: tracked clean, auxiliary, malformed, prompt-injected, legacy poisoned, and sample document corpora.
- `docker-compose.yml`: local multi-service development/demo stack.
- `coursework/` and `docs/`: capstone deliverables, specs, test packs, and supporting reports.

The core value proposition remains: ingest PDF/DOCX/PPTX documents, embed chunks and titles, retrieve through hybrid semantic/BM25/title search, optionally rerank with Cohere, and expose searchable results and document previews in a desktop-style web UI.

---

## Decision 1: Unified PostgreSQL Search Store

**Decision:** Use a single ParadeDB PostgreSQL instance for metadata, document chunks, pgvector semantic search, title vector search, users, and query logs.

**Current evidence:**

- `docker-compose.yml`: `db` uses `paradedb/paradedb:latest`.
- `backend/db/init.sql`: enables `uuid-ossp`, `vector`, and `pg_search`.
- `backend/app/models/db.py`: defines `Document`, `DocumentChunk`, `DocumentTitleEmbedding`, `User`, and `QueryLog`.
- `backend/app/services/search.py`: raw SQL handles pgvector and ParadeDB BM25 queries.

**Rationale:** One database keeps the prototype operationally simple. It avoids running separate Elasticsearch/OpenSearch, Pinecone, Weaviate, or Qdrant infrastructure for a capstone-sized corpus while still supporting both vector and keyword retrieval.

**Current schema highlights:**

- `documents`: metadata, access level, version group, content hash, cached AI summary fields.
- `document_chunks`: text chunks with `vector(1024)` embeddings.
- `document_title_embeddings`: one `vector(1024)` title embedding per document.
- `users`: demo auth users and roles.
- `query_logs`: audit/analytics table, currently unused by application code.

**Tradeoffs:**

- Good: simpler local setup, SQL access for debugging, one backup boundary, no search cluster.
- Good: ParadeDB BM25 and pgvector can be fused without cross-service joins.
- Cost: raw SQL is necessary for pgvector and ParadeDB-specific operators.
- Cost: no migrations are present; schema changes are handled through `init.sql` and local database resets.
- Cost: scale and relevance tuning are unproven beyond prototype/test corpora.

---

## Decision 2: Dedicated Title Embeddings

**Decision:** Store title embeddings in `document_title_embeddings` rather than on the `documents` table or mixed into regular chunks.

**Current evidence:**

- `backend/db/init.sql`: `document_title_embeddings` table and HNSW index.
- `backend/app/models/db.py`: `DocumentTitleEmbedding` relationship.
- `backend/app/services/ingestion.py`: embeds `[title] + chunks` and stores the first vector as the title embedding.
- `backend/app/services/search.py`: title similarity is a third retrieval list merged by RRF.

**Rationale:** Title matching is a separate relevance signal. Keeping it separate makes metadata fetches cheaper, keeps chunk and title indexes independently tunable, and avoids pretending a title is just another body chunk.

**Tradeoffs:**

- Good: explicit title boost without distorting chunk content.
- Good: compact HNSW index over one row per document.
- Cost: ingestion must maintain one extra row and index.
- Cost: title-only matches need synthetic result entries in RRF because they may not correspond to a body chunk hit.

---

## Decision 3: Hybrid Retrieval With RRF

**Decision:** Search uses three candidate lists:

1. Semantic chunk search with pgvector cosine distance.
2. BM25 chunk search with ParadeDB.
3. Semantic title search with pgvector cosine distance.

The lists are merged with Reciprocal Rank Fusion (RRF), then optionally reranked by Cohere.

**Current evidence:**

- `backend/app/services/search.py`: `hybrid_search()`, `_rrf_merge()`, `_sanitize_bm25_query()`, `_filter_latest_versions()`.
- `backend/app/core/config.py`: `SEARCH_TOP_K=50`, `RERANK_TOP_N=10`, `RRF_K=60`, `TITLE_BOOST_WEIGHT=1.5`.

**Current flow:**

```text
query
  -> generate query embedding
  -> semantic chunk search
  -> BM25 chunk search
  -> title embedding search
  -> weighted RRF merge
  -> Cohere rerank, or passthrough if unavailable
  -> document metadata fetch
  -> collapse duplicate documents
  -> latest-version filter when enabled
  -> response
```

**Rationale:** Pure vector search can miss exact names, acronyms, and filenames. Pure BM25 misses paraphrases. Title search improves cases where the user knows a policy/report/deck name. RRF avoids fragile score normalization between cosine similarity and BM25 scores.

**Implementation notes:**

- BM25 punctuation/operator characters are stripped before calling `paradedb.parse()`.
- BM25 and title search failures roll back the transaction and continue with remaining signals.
- Query embedding failure raises `EmbeddingServiceUnavailable`, mapped to a 503 by `backend/app/main.py`.
- Service-layer category and `doc_type` filters exist.
- The frontend sends `doc_type` filters, but its "authorized" filter sends `access_level`, which `hybrid_search()` currently ignores.

**Tradeoffs:**

- Good: robust ranking for a mixed corporate corpus.
- Good: RRF keeps retrieval math simple and explainable.
- Cost: each query can execute three search SQL statements plus document metadata fetch.
- Cost: filtering latest versions after reranking can reduce the final result count.
- Cost: frontend access-level filter UI does not currently match backend filter support.

---

## Decision 4: Qwen3 Embedding Service Out of Process

**Decision:** Run `Qwen/Qwen3-Embedding-0.6B` behind an HTTP `/embed` service instead of loading the model inside the FastAPI backend process.

**Current evidence:**

- `embedding_server.py`: FastAPI server using `SentenceTransformer`, GPU/CPU auto-detection, `/embed`, `/health`.
- `embedding.Dockerfile`: CUDA image for NVIDIA GPU hosts.
- `embedding.cpu.Dockerfile`: CPU-only fallback image.
- `docker-compose.yml`: `embedding` service, health check, Hugging Face cache volume.
- `docker-compose.cpu.yml`: override to use the CPU Dockerfile and remove GPU reservations.
- `backend/app/services/embeddings.py`: batches requests through `EMBEDDING_API_URL`.

**Rationale:** The embedding model is heavyweight relative to the API. Keeping it in its own service isolates model dependencies, makes CPU/GPU deployment selectable, and lets the backend stay focused on orchestration and persistence.

**Current contract:**

```http
POST /embed
{"texts": ["..."]}

200
{"embeddings": [[...]]}
```

**Implementation notes:**

- Embeddings are normalized by the model server.
- Backend batch size is controlled by `EMBED_BATCH_SIZE=64`.
- Backend timeout is 300 seconds to tolerate large ingestion batches and cold model behavior.
- Docker default expects `EMBEDDING_API_URL` from `.env`; the example currently sets `http://localhost:8001/embed`, which is correct for standalone backend but should be changed to `http://embedding:8001/embed` for backend-in-Docker.

**Tradeoffs:**

- Good: model isolation, easier GPU/CPU swaps, clearer failure mode.
- Good: FastAPI backend does not pay model import/startup costs.
- Cost: search and ingestion hard-depend on the embedding service.
- Cost: first run downloads a large model into local cache.
- Cost: CPU profile is available but likely much slower.

---

## Decision 5: Optional Cohere Reranking and Summaries

**Decision:** Use Cohere for two optional AI capabilities:

- `rerank-v3.5` reranks candidate chunks after RRF.
- `command-r-08-2024` generates cached document-detail summaries.

**Current evidence:**

- `backend/app/services/reranker.py`: returns original order when `COHERE_API_KEY` is missing or the call fails.
- `backend/app/services/summarizer.py`: calls Cohere Chat and raises `SummarizerUnavailable` on missing key, empty content, or upstream failure.
- `backend/app/api/documents.py`: `GET /api/documents/{doc_id}/summary` caches summary text on `documents.summary`.
- `frontend/src/components/DocumentSummaryPanel/DocumentSummaryPanel.tsx`: document detail summary UI.

**Rationale:** Reranking can improve precision without changing the first-stage retrieval design. Summaries improve document triage on the detail page. Both features degrade in controlled ways when the Cohere key is absent.

**Important current behavior:**

- Search still works without Cohere rerank.
- Document summaries do not work without `COHERE_API_KEY`; the API returns a 503 and the frontend shows an unavailable message.
- Commit `ffdb0b1` reverted "summarize from search results", so summaries are no longer fetched or shown directly in the search results list. The document detail summary panel remains.

**Tradeoffs:**

- Good: optional quality/UX boost.
- Good: summaries are cached in the database after first generation.
- Cost: summaries introduce LLM cost and latency.
- Cost: no prompt-injection mitigation is applied to document content sent to summarization beyond prompt wording.
- Cost: no cache invalidation beyond upload/reingest paths that update document rows.

---

## Decision 6: Docling for Multi-Format Parsing

**Decision:** Use Docling as the parser for PDF, DOCX, and PPTX files.

**Current evidence:**

- `backend/requirements.txt`: `docling==2.31.0`.
- `backend/app/services/ingestion.py`: `DocumentConverter` with `InputFormat.PDF`, `InputFormat.DOCX`, `InputFormat.PPTX`.
- PPTX uses `PowerpointFormatOption(pipeline_cls=SimplePipeline)`.

**Rationale:** A single parser library reduces code paths for the three supported enterprise document formats. Exporting to markdown gives a consistent text representation for chunking and embedding.

**Ingestion choices:**

- Compute SHA-256 content hash before parsing.
- Derive title from cleaned filename unless an upload title is provided.
- Chunk by words with `CHUNK_SIZE=512` and `CHUNK_OVERLAP=50`.
- Embed title and chunks in one batched request.
- Store chunks and title embedding in one transaction.
- Lazily create the BM25 index after chunks exist.

**Tradeoffs:**

- Good: unified parser, simple chunks, deterministic filename titles.
- Good: unchanged files are skipped through content hash checks.
- Cost: parsing happens in the backend process, only shifted to a thread with `asyncio.to_thread`.
- Cost: chunking is word-based, not tokenizer-aware.
- Cost: malformed documents are handled by ingestion script exception logging, not by rich structured diagnostics.

---

## Decision 7: Filename-Based Versioning

**Decision:** Detect versions with a trailing `_vN` filename convention and group otherwise similar files through normalized stems.

**Current evidence:**

- `backend/app/services/ingestion.py`: `_extract_version_info()`.
- `backend/db/init.sql`: `document_group`, `version`, and `UNIQUE (document_group, version)`.
- `backend/app/services/search.py`: `_filter_latest_versions()`.
- `backend/app/models/schemas.py`: `SearchRequest.show_latest_only`, `SearchResultItem.version`, `SearchResultItem.document_group`.

**Rationale:** Enterprise files often already use names like `Remote_Work_Policy_v2.docx`. Filename detection avoids a metadata editor or manual uploader workflow.

**Current examples:**

- `Remote_Work_Policy_v2.docx` -> group `remote work policy`, version `2`.
- `Acceptable_Use_Policy.pdf` -> group `acceptable use policy`, version `1`.

**Tradeoffs:**

- Good: deterministic and easy to explain.
- Good: duplicate version rows are prevented.
- Cost: relies on naming discipline.
- Cost: if the same group/version changes, ingestion deletes and replaces the previous row.
- Cost: there is no UI to browse all versions; the frontend always sends `show_latest_only: true`.

---

## Decision 8: Document Detail, Preview, and Conversion

**Decision:** Provide document detail pages with raw download, extracted text, PDF preview, and AI summary. Convert DOCX/PPTX previews to PDF through Gotenberg.

**Current evidence:**

- Backend:
  - `GET /api/documents/{doc_id}`
  - `GET /api/documents/{doc_id}/chunks`
  - `GET /api/documents/{doc_id}/file`
  - `GET /api/documents/{doc_id}/preview`
  - `GET /api/documents/{doc_id}/summary`
- `backend/app/services/pdf_conversion.py`: Gotenberg conversion and cache.
- `docker-compose.yml`: `gotenberg/gotenberg:8` service.
- `frontend/src/pages-views/DocumentPage/DocumentPage.tsx`: preview/text tabs, download, summary side panel.

**Rationale:** Search results are only useful if users can inspect and retrieve the source document. Normalizing preview output to PDF gives the browser a stable rendering path for supported Office formats.

**Tradeoffs:**

- Good: works for PDF directly and DOCX/PPTX through conversion.
- Good: converted PDFs are cached by document id under `/data/converted`.
- Cost: Gotenberg is another service dependency.
- Cost: no authentication or authorization is applied to file, preview, chunks, or summary endpoints.
- Cost: conversion failures surface as 502 responses.

---

## Decision 9: FastAPI Service Layer

**Decision:** Keep a conventional FastAPI layering:

```text
api/ routers -> services/ business logic -> models/ ORM and schemas -> core/ config, database, DI
```

**Current evidence:**

- `backend/app/main.py`: CORS, exception handlers, lifespan DB count, router includes.
- `backend/app/api/`: health, auth, documents, search.
- `backend/app/services/`: auth, embeddings, ingestion, pdf conversion, reranker, search, summarizer, validation.
- `backend/app/core/`: config, database, dependency re-export.

**Rationale:** The backend is API-first and mostly asynchronous. FastAPI and Pydantic give request validation and OpenAPI docs with low ceremony.

**Tradeoffs:**

- Good: straightforward local development and clean route/service separation.
- Good: async SQLAlchemy and async HTTP clients fit search/embedding workloads.
- Cost: no dependency injection for auth roles is used on protected routes.
- Cost: no migration framework, structured logging policy, or test harness.

---

## Decision 10: JWT Auth Designed but Not Enforced

**Decision:** Implement backend JWT login and role primitives, but leave the demo search/upload/document endpoints unauthenticated.

**Current evidence:**

- `backend/app/api/auth.py`: `POST /api/auth/login`.
- `backend/app/services/auth.py`: bcrypt hashing/verification, HS256 JWT creation, token decode helper.
- `backend/db/init.sql`: seeded `admin`, `manager`, `analyst` users.
- `backend/app/api/search.py`: hardcodes `user_role = "admin"`.
- `frontend/src/api/account.ts`: returns a static demo admin user.

**Rationale:** The prototype prioritized search, ingestion, preview, and demo UI. The backend has the pieces needed to wire auth later, but the current user experience does not include real login/session handling.

**Current role design:**

- `analyst`: public.
- `manager`: public + internal.
- `admin`: public + internal + confidential.

**Current gaps:**

- Search always runs as admin.
- Upload has no admin check.
- Document file, preview, chunk, and summary endpoints have no auth checks.
- Frontend has no login flow and no token storage.
- `SECRET_KEY` is hardcoded in `backend/app/services/auth.py`.
- `.env.example` includes NextAuth variables even though NextAuth is not installed or used in this checkout.

**Tradeoffs:**

- Good: simple demo flow.
- Cost: not production-safe and not a realistic enterprise security posture.

---

## Decision 11: Frontend as Client-Only Next.js Shell

**Decision:** Use Next.js 16 Pages Router only as a host for a browser-only React Router application.

**Current evidence:**

- `frontend/src/pages/[[...slug]].tsx`: dynamically imports `@/App` with `ssr: false`.
- `frontend/src/App.tsx`: `BrowserRouter`, `Routes`, `Route`.
- Routes:
  - `/`
  - `/results`
  - `/account`
  - `/document/:id`
- `frontend/package.json`: `next@16.2.3`, `react@19.2.4`, `react-router-dom@7.14.0`, `sass`.
- `frontend/Dockerfile`: `node:20-alpine`, `npm ci`, `npm run dev`.

**Rationale:** The current UI behaves like a desktop document-search app with persistent layout, sidebar, localStorage state, and client-side navigation. Disabling SSR avoids hydration problems with React Router and browser-only APIs.

**Current frontend features:**

- Search landing page with greeting and filters.
- Results page with cached search responses and inline service errors.
- File type and date filters.
- "Authorized" filter UI, although backend support is not wired correctly.
- Document detail page with PDF preview, extracted text, download, and AI summary.
- Account page backed by a demo user.
- Dark/light theme persisted in localStorage.
- Pinned documents and recents persisted per demo user in localStorage.

**Tradeoffs:**

- Good: fast implementation of a rich SPA-style prototype.
- Good: persistent UX state is easy with contexts and localStorage.
- Cost: gives up Next.js SSR/streaming advantages.
- Cost: stale App Router/shadcn docs no longer match implementation.
- Cost: no real auth/session integration.

---

## Decision 12: Docker Compose Demo Stack

**Decision:** Use Docker Compose for local orchestration.

**Current evidence:**

- `docker-compose.yml` defines `db`, `embedding`, `backend`, `gotenberg`, and `frontend`.
- `docker-compose.cpu.yml` swaps in the CPU embedding image for non-NVIDIA hosts.
- `.env.example` documents DB, embedding, Cohere, backend, and Gotenberg settings.

**Current services:**

| Service | Role | Port |
| --- | --- | --- |
| `db` | ParadeDB PostgreSQL | `5432` |
| `embedding` | Qwen embedding API | `8001` |
| `backend` | FastAPI API | `8000` |
| `gotenberg` | DOCX/PPTX -> PDF conversion | internal `3000` |
| `frontend` | Next.js dev server | `3000` |

**Rationale:** Compose is enough for capstone/demo operation and keeps the stack inspectable.

**Current startup behavior:**

- `docker compose up -d` starts the services and waits on DB/embedding/backend health checks.
- The backend lifespan logs the current document count.
- It does not auto-ingest documents. Use `docker compose exec backend python -m app.scripts.ingest_all`.

**Tradeoffs:**

- Good: reproducible local stack.
- Good: CPU override supports MacBooks and other non-NVIDIA machines.
- Cost: dev-mode servers and volume mounts are not production deployment.
- Cost: no production secrets, TLS, backups, migrations, or scaling strategy.

---

## Decision 13: Multi-Corpus Test Data

**Decision:** Keep multiple document categories in-repo for clean demos and adversarial/edge-case testing.

**Current evidence:**

- `data/generic`: 6 enterprise appendix-style files.
- `data/auxiliary`: 52 curated corporate policies, reports, and presentations.
- `data/malformed`: 6 intentionally broken or malformed files.
- `data/prompt-injected`: 6 intentionally instruction-laced files.
- `data/poisoned`: legacy poisoned/conflicting corpus.
- `data/sample` and `data/sample-docs`: older sample files.
- `backend/app/scripts/ingest_all.py`: supports `--mode`, `--poisoned`, `--all`, `--categories`, `--dirs`, `--recursive`, `--limit`, and `--clean`.

**Rationale:** The project needs both a clean enterprise-search demo corpus and test material for parser robustness, prompt-injection resilience, poisoned results, versioning, and malformed inputs.

**Tradeoffs:**

- Good: repeatable local evaluation.
- Good: edge cases are visible and not hidden in external storage.
- Cost: repo size increases with binary documents.
- Cost: no automated assertion suite consumes the test pack yet.

---

## Decision 14: Manual and Documented QA Over Automated Tests

**Decision:** The codebase currently relies on manual/API/UI checks and documented edge-case runs rather than automated tests.

**Current evidence:**

- `backend/tests/` contains only `__init__.py`.
- No test scripts are defined in backend requirements or frontend `package.json`.
- `docs/test-runs/2026-04-16-results.md` records manual edge-case results.
- `docs/search-agent-edge-case-test-pack.md` defines cases but is not wired into CI.

**Rationale:** The capstone prototype focused on feature completion and demo readiness.

**Tradeoffs:**

- Good: faster early prototyping.
- Cost: no regression protection for search, ingestion, preview conversion, auth, or frontend routing.
- Cost: issues like frontend/backend filter mismatches can persist unnoticed.

---

## Security and Operations Position

The current project is a functioning academic prototype, not production software.

Implemented safeguards:

- Pydantic validation for query length and required fields.
- Prompt-injection regex blocklist for obvious query attacks.
- BM25 query sanitization for Tantivy operator characters.
- Parameterized SQL values in raw search queries.
- bcrypt password hashes for seeded demo users.
- 503 handlers for embedding and summarizer unavailability.
- Extension checks for uploads.

Current production blockers:

- JWT secret is hardcoded.
- Search, upload, file, preview, chunks, and summary endpoints are unauthenticated.
- Search hardcodes admin access.
- Frontend does not log in or pass bearer tokens.
- Upload validation is extension-only and has no file size limit.
- CORS is wildcard with credentials enabled.
- No rate limiting.
- No audit writes to `query_logs`.
- No security headers.
- No structured logs, metrics, alerts, migrations, backups, or CI.

---

## Git History Decision Timeline

Visible local/remote history shows these major phases:

| Phase | Representative commits | Architectural impact |
| --- | --- | --- |
| MVP foundation | `6b6c03d` | FastAPI, original Next frontend, ParadeDB/pgvector, Docling, hybrid search, JWT primitives, Docker Compose. |
| Early stabilization | `13924cf`, `0c5348c`, `2a62303`, `fb60be8` | Secrets moved to env, frontend package experiments, local embedding server, removal of silent mock fallback/API fixes. |
| Title/version ranking | `90ab37f` | Dedicated title embeddings, weighted RRF, version grouping, latest-only filtering, BM25 sanitization. |
| Startup/data/test expansion | `1a2ff4a`, `f917e81`, `e96da3b` | Startup planning, Docker/data improvements, finalized auxiliary and edge-case corpora. |
| CPU and document UX | `a90799c`, `c49ad1b`, `464b90d`, `92f164d` | CPU embedding override, document preview page, pins/recents, search-result cache, download filename fix. |
| Repo cleanup/frontend relocation | `6603889` | `Fetch/` renamed to `frontend/`; coursework consolidated. |
| Gotenberg preview | `da5d5dc` | DOCX/PPTX previews via Gotenberg PDF conversion. |
| AI summaries | `6d51da9`, `2edfcf3` | Document-detail summary service, DB cache fields, summary panel. |
| Search-result summaries reverted | `3fea768`, `ffdb0b1` | Summary previews in search results were added then reverted; document-detail summary remains. |

Current branch note: local `main` is `ahead 1, behind 34` relative to `origin/main`. The remote history after this local checkout appears focused mostly on final-report polish and some frontend/cloud-embedding follow-up commits. Those remote changes are not reflected in the local working tree until merged or rebased.

---
