# Technical Architecture Report
## AI-Driven Company-Wide Search Engine for Deloitte Resources

**Purpose:** This document serves as the comprehensive technical guide for the Software Engineering Assignment. It defines the system architecture, data flow, user flow, security model, and deployment strategy — informed by industry best practices from Glean, Elastic Enterprise Search, Microsoft Search/Copilot, Coveo, and Algolia.

**Group Two:** Jesse Gabriel, Andrew Jung, Raven Levitt, Felix Tian, Sophia Turnbow, Matthew Voynovich

**ITWS 4100 — Information Technology Capstone — Spring 2026**

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Overview & Problem Statement](#2-system-overview--problem-statement)
3. [Architecture Deep Dive](#3-architecture-deep-dive)
4. [Data Flow Architecture](#4-data-flow-architecture)
5. [User Flow & UX Architecture](#5-user-flow--ux-architecture)
6. [NLP & Search Pipeline](#6-nlp--search-pipeline)
7. [Security Architecture](#7-security-architecture)
8. [Deployment & Infrastructure](#8-deployment--infrastructure)
9. [Performance & Scalability](#9-performance--scalability)
10. [Technology Stack Justification](#10-technology-stack-justification)
11. [Use Case Deep Dive](#11-use-case-deep-dive)
12. [Diagram Descriptions & Rationale](#12-diagram-descriptions--rationale)
13. [Gap Analysis: Current Draft vs. This Report](#13-gap-analysis-current-draft-vs-this-report)
14. [References](#14-references)

---

## 1. Executive Summary

This report provides the authoritative technical specification for the Deloitte AI-Driven Search Engine. The system is an enterprise search platform that allows Deloitte employees to find internal resources (documents, policies, slide decks, images) using natural language queries. It addresses the well-documented problem that 62% of knowledge workers spend excessive time searching for information (Microsoft, 2023), with an average of 2.8 hours/week lost to locating or requesting needed information (APQC, 2021).

The architecture follows established enterprise search patterns validated by industry leaders:

| Design Decision | Industry Precedent |
|---|---|
| Hybrid retrieval (semantic + keyword) | Elastic, Azure AI Search, Weaviate, Glean |
| Reciprocal Rank Fusion for result merging | Elastic, Azure AI Search, OpenSearch |
| Query-time access control filtering | Glean, Microsoft Search, Coveo |
| Parallel retrieval pipelines | All major enterprise search platforms |
| Document-level permissions with pre-filtering | Azure AI Search, Glean |
| Semantic caching for repeated queries | Redis LangCache, Glean |

The system uses a four-layer architecture (Frontend, API, Processing, Data) deployed via Docker containers with a unified PostgreSQL database (extended with pgvector and ParadeDB), achieving sub-2-second response times for 95% of queries.

---

## 2. System Overview & Problem Statement

### 2.1 The Problem

Deloitte's ~470,000 employees across 700+ locations rely on multiple internal platforms to access company documents, policies, slide decks, and images. The core problems are:

1. **Fragmented search**: Resources are scattered across platforms; users must navigate multiple tools.
2. **Vocabulary mismatch**: Users often cannot describe what they need using the exact terms used in document titles or metadata.
3. **Lost productivity**: At Deloitte's scale, even a modest improvement in search efficiency recovers significant billable capacity. Industry-wide, professional services billable utilization averaged 68.9% in 2024, below the 70-75% optimal threshold (SPI Research, 2025).

### 2.2 The Solution

A unified search engine with:
- **One search bar** accepting natural language queries
- **NLP-powered intent understanding** (not just keyword matching)
- **Hybrid retrieval** combining semantic similarity with keyword matching
- **Defined query boundaries** with input validation, content filtering, and rate limiting
- **Built-in user guidance** (suggestions, "Did you mean?", search tips)
- **A searchable resource database** with a unified PostgreSQL store (metadata, vectors via pgvector, and BM25 keyword search via ParadeDB)

### 2.3 Deliverables (from Deloitte's Project Brief)

| # | Deliverable | Status |
|---|---|---|
| D1 | Defined use cases and requirements | Addressed in this report and SE assignment |
| D2 | Market research on NLP security and boundaries | Addressed in Section 7 |
| D3 | Technical design (architecture diagrams + documentation) | Core of this report and SE assignment |
| D4 | Functioning web application prototype | Development phase |

---

## 3. Architecture Deep Dive

### 3.1 High-Level Architecture (Four Layers)

The system follows a layered architecture pattern, with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────────┐
│                       FRONTEND LAYER                            │
│  Next.js (App Router) + TypeScript + Vercel AI SDK 6            │
│  UI: AI Elements + shadcn/ui                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │ Search   │ │ Filter   │ │ Results  │ │ User Guidance    │  │
│  │ Interface│ │ Panel    │ │ Display  │ │ (Tips, Did you   │  │
│  │          │ │          │ │          │ │  mean?, Walkthru)│  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────────────┘  │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTPS / REST API
┌────────────────────────────┼────────────────────────────────────┐
│                       API LAYER                                 │
│  FastAPI + Uvicorn ASGI + LlamaIndex (retrieval orchestration)  │
│  ┌──────────────────┐ ┌──────────────────┐                     │
│  │ Auth & RBAC      │ │ Rate Limiter     │                     │
│  │ Middleware        │ │ Middleware       │                     │
│  └──────────────────┘ └──────────────────┘                     │
│  ┌──────────────────────────────────────────┐                  │
│  │ API Router (POST /api/search, etc.)      │                  │
│  └──────────────────────────────────────────┘                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                    PROCESSING LAYER                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────────┐   │
│  │ Input        │ │ NLP Engine   │ │ Ranking Service      │   │
│  │ Validator &  │ │ - Intent     │ │ - RRF Fusion         │   │
│  │ Content      │ │   Classifier │ │ - Cohere Rerank 4    │   │
│  │ Filter       │ │ - Embedding  │ │ - Metadata Re-rank   │   │
│  │              │ │   Generator  │ │                      │   │
│  └──────────────┘ └──────────────┘ └──────────────────────┘   │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                       DATA LAYER                                │
│  ┌────────────────────────────────┐ ┌──────────────────────┐   │
│  │ Unified PostgreSQL 16          │ │ Document Ingestion   │   │
│  │ + pgvector + ParadeDB          │ │ Pipeline             │   │
│  │                                │ │ - Docling (IBM)      │   │
│  │ - Metadata store               │ │   document parser    │   │
│  │ - Vector store (pgvector)      │ │ - Format Detection   │   │
│  │ - BM25 keyword search          │ │ - Text Extraction    │   │
│  │   (ParadeDB)                   │ │ - Chunking           │   │
│  │ - Audit logs                   │ │ - Embedding Gen      │   │
│  │ - User/role data               │ │ - Index Storage      │   │
│  └────────────────────────────────┘ └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Why This Architecture

**Layered separation** is the standard for enterprise search systems. Glean, Elastic, and Microsoft Search all use similar patterns where the retrieval layer is decoupled from the API layer and the frontend. This provides:

- **Independent scaling**: The NLP/embedding computation (most CPU/GPU-intensive) can scale independently from the API layer.
- **Technology substitution**: Swapping components (e.g., the embedding model or search extensions) requires changes only in the Data Layer.
- **Testability**: Each layer can be tested in isolation.
- **Security boundaries**: The API Layer acts as a single entry point with authentication, authorization, and rate limiting enforced before any processing occurs.

### 3.3 Component Interactions

| Source Component | Target Component | Protocol / Method | Purpose |
|---|---|---|---|
| Browser | Next.js Frontend | HTTPS | Serve the application (SSR + client) |
| Next.js Frontend | FastAPI Backend | REST API (JSON) | All search/filter/ingest operations |
| FastAPI | Input Validator | Internal function call | Sanitize and validate queries |
| FastAPI | NLP Engine (LlamaIndex) | Internal function call | Intent classification + embedding |
| NLP Engine | Qwen3-Embedding-0.6B Model | Model inference | Generate 1024-dim vectors |
| FastAPI | PostgreSQL (pgvector) | SQL via ORM (SQLAlchemy) | Semantic similarity search |
| FastAPI | PostgreSQL (ParadeDB) | SQL via ORM (SQLAlchemy) | BM25 keyword search |
| FastAPI | PostgreSQL | SQL via ORM (SQLAlchemy) | Metadata queries, audit logs |
| FastAPI | Ranking Service | Internal function call | RRF fusion + Cohere Rerank 4 + re-ranking |
| Ranking Service | Cohere Rerank 4 | REST API | Neural reranking of fused results (+33-40% accuracy) |
| Ingestion Pipeline | Docling (IBM) | Internal function call | Document parsing (PDF, DOCX, PPTX, images) |
| Ingestion Pipeline | PostgreSQL | SQL via ORM | Store document metadata, chunk vectors, and full text |
| Ingestion Pipeline | Qwen3-Embedding-0.6B Model | Model inference | Generate embeddings for documents |

---

## 4. Data Flow Architecture

### 4.1 Query-Time Data Flow (Search Request)

This is the critical path — what happens when a user searches.

```
User types query
       │
       ▼
┌──────────────────┐
│  1. INPUT        │  Validate length, language, content filters.
│     VALIDATION   │  Block PII, prompt injection, profanity.
│                  │  If invalid → return 400 + guidance message.
└────────┬─────────┘
         │ (valid query)
         ▼
┌──────────────────┐
│  2. QUERY        │  Intent classification (navigational vs. informational).
│     UNDERSTANDING│  Entity extraction (topic, date, doc type, person).
│                  │  Spell correction, query expansion.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  3. EMBEDDING    │  Convert query text → 1024-dim dense vector
│     GENERATION   │  using Qwen3-Embedding-0.6B model.
└────────┬─────────┘
         │
         ├─────────────────────────────┐
         ▼                             ▼
┌──────────────────┐      ┌──────────────────┐
│  4a. SEMANTIC    │      │  4b. KEYWORD     │
│      SEARCH      │      │      SEARCH      │
│                  │      │                  │
│  PostgreSQL +    │      │  PostgreSQL +    │
│  pgvector:       │      │  ParadeDB:       │
│  cosine_sim(     │      │  BM25 full-text  │
│    query_vector, │      │  search against  │
│    doc_vectors)  │      │  title + content │
│  top_k = 50      │      │  top_k = 50      │
└────────┬─────────┘      └────────┬─────────┘
         │                         │
         └───────────┬─────────────┘
                     ▼
         ┌──────────────────┐
         │  5. RECIPROCAL   │  RRF score = Σ 1/(k + rank_i)
         │     RANK FUSION  │  k = 60 (standard)
         │                  │  Merge semantic + keyword rankings.
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  5b. RERANKING   │  Cohere Rerank 4 neural reranker.
         │     (Cohere)     │  Re-score top candidates using
         │                  │  cross-attention over query + passage.
         │                  │  +33-40% accuracy improvement.
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  6. METADATA     │  Apply user's filters (doc type, date, author).
         │     FILTERING &  │  Enforce RBAC permissions.
         │     RBAC         │  Remove unauthorized results.
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  7. RESULT       │  Assemble response: title, snippet, author,
         │     ASSEMBLY     │  date, document type, relevance score.
         │                  │  Generate "Did you mean?" if needed.
         └────────┬─────────┘
                  │
                  ▼
         ┌──────────────────┐
         │  8. LOGGING      │  Log query, user_id, result_count,
         │                  │  latency, selected_result (on click).
         └────────┬─────────┘
                  │
                  ▼
         Return JSON response to frontend
```

**Industry context:** This multi-stage pipeline (query understanding → parallel retrieval → fusion → reranking → filtering) is the standard architecture used by Elastic Enterprise Search, Azure AI Search, and Glean. The parallel retrieval step is critical — running BM25 and vector search simultaneously rather than sequentially halves the retrieval latency. Because both search paths now execute within the same PostgreSQL instance (ParadeDB for BM25, pgvector for semantic), the parallel queries share the same connection and eliminate inter-service network hops, further reducing latency.

### 4.2 Ingestion-Time Data Flow (Document Indexing)

This is the offline pipeline — what happens when new documents are added.

```
Admin uploads document(s)
       │
       ▼
┌──────────────────┐
│  1. DOCUMENT     │  Docling (IBM) handles unified parsing.
│     PARSING      │  97.9% accuracy on complex table extraction.
│     (Docling)    │  Supports PDF, DOCX, PPTX, images, HTML.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  2. FORMAT       │  Detect MIME type (PDF, DOCX, PPTX, image).
│     DETECTION    │  Route to appropriate Docling pipeline.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  3. CONTENT      │  Docling extracts text with layout awareness.
│     EXTRACTION   │  Tables, headings, and structure preserved.
│                  │  OCR fallback for scanned documents.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  4. METADATA     │  Extract: title, author, creation date, doc type,
│     EXTRACTION   │  page count, file size, headings/sections.
│                  │  Assign unique document_id (UUID).
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  5. CHUNKING     │  Strategy: Recursive character splitting.
│                  │  Chunk size: 400–512 tokens.
│                  │  Overlap: 10–20% (50–100 tokens).
│                  │  Heading-aware: preserve section context.
│                  │  Each chunk gets: chunk_id, document_id,
│                  │  section_header, position_in_doc.
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│  6. EMBEDDING    │  Each chunk → Qwen3-Embedding-0.6B → 1024-dim vector.
│     GENERATION   │  Batch processing for efficiency.
└────────┬─────────┘
         │
         ▼
┌──────────────────────────────────────────┐
│  7. UNIFIED POSTGRESQL STORE             │
│                                          │
│  Single INSERT per chunk writes:         │
│  - Chunk text (for ParadeDB BM25 index)  │
│  - Embedding vector (pgvector column)    │
│  - Document metadata (relational cols)   │
│  - Access control tags                   │
│                                          │
│  No duplicate metadata. No network hops. │
└──────────────────────────────────────────┘
```

**Key design decisions for the ingestion pipeline:**

| Decision | Rationale | Industry Precedent |
|---|---|---|
| Docling (IBM) for parsing | Unified document parser with 97.9% accuracy on complex table extraction. Handles PDF, DOCX, PPTX, images, and HTML with layout-aware extraction. | IBM Research, LlamaIndex integration |
| 400–512 token chunks | NAACL 2025 research shows fixed ~200-word chunks perform as well as semantic chunking with much lower computational cost. 400–512 tokens balances factoid and analytical queries. | Elastic, LangChain defaults |
| 10–20% overlap | Prevents information loss at chunk boundaries. | Weaviate, LlamaIndex best practice |
| Heading-aware splitting | Preserves section context, critical for well-structured Deloitte documents (reports, policies). | Unstructured.io, LlamaIndex |
| Unified PostgreSQL store (pgvector + ParadeDB) | Single database handles vectors, BM25 keyword search, metadata, and audit logs. Eliminates duplicate metadata, removes network hops for vector search, and simplifies operations. | pgvector adoption by Supabase, Neon; ParadeDB for hybrid search |
| Unique document IDs | Links chunks to document metadata within the same PostgreSQL database. Enables document-level operations (delete, update) with referential integrity. | Standard in all enterprise search |

### 4.3 Data Model

#### PostgreSQL Schema (Unified Store — pgvector + ParadeDB)

PostgreSQL serves as the single data store for the entire system. The `pgvector` extension adds vector column types and similarity search operators. The `ParadeDB` extension (pg_search) adds BM25 full-text search with relevance scoring. This eliminates the need for an external vector database, removes duplicate metadata, and provides ACID guarantees across all data.

```
-- Extensions enabled:
-- CREATE EXTENSION vector;        (pgvector — vector similarity search)
-- CREATE EXTENSION pg_search;     (ParadeDB — BM25 keyword search)

documents
├── document_id       UUID (PK)
├── title             VARCHAR
├── author            VARCHAR
├── created_date      TIMESTAMP
├── document_type     ENUM (pdf, docx, pptx, image)
├── file_size_bytes   INTEGER
├── page_count        INTEGER
├── source_path       VARCHAR
├── access_level      ENUM (public, internal, confidential, restricted)
├── ingested_at       TIMESTAMP
└── updated_at        TIMESTAMP

chunks
├── chunk_id          UUID (PK)
├── document_id       UUID (FK → documents)
├── chunk_text        TEXT
├── embedding         VECTOR(1024)    ← pgvector column (Qwen3-Embedding-0.6B output)
├── section_header    VARCHAR
├── position          INTEGER
├── token_count       INTEGER
└── created_at        TIMESTAMP
    -- INDEX: HNSW index on embedding column for vector similarity search
    -- INDEX: ParadeDB BM25 index on chunk_text for keyword search

search_logs
├── log_id            UUID (PK)
├── user_id           VARCHAR
├── query_text        TEXT
├── intent            VARCHAR
├── result_count      INTEGER
├── selected_doc_id   UUID (FK → documents, nullable)
├── latency_ms        INTEGER
└── created_at        TIMESTAMP

users
├── user_id           VARCHAR (PK)
├── role              ENUM (employee, admin)
├── department        VARCHAR
└── last_active       TIMESTAMP
```

**Why a unified store?** By co-locating vectors, full text, and metadata in a single PostgreSQL instance, we eliminate the architectural complexity of synchronizing two data stores, remove network latency for vector search queries, and avoid duplicating metadata across systems. Pre-filtering by `access_level` or `document_type` happens natively in SQL WHERE clauses that apply to both vector and keyword searches — the same pattern used by Glean and Azure AI Search, but without the operational overhead of an external vector database service.

---

## 5. User Flow & UX Architecture

### 5.1 Primary User Flow (Search)

```
┌─────────────────────────────────────────────────────────────┐
│                    USER JOURNEY MAP                          │
│                                                             │
│  1. ARRIVE          2. SEARCH          3. REFINE           │
│  ┌────────────┐    ┌────────────┐    ┌────────────┐       │
│  │ Landing    │───▶│ Type query │───▶│ View       │       │
│  │ page with  │    │ in search  │    │ ranked     │       │
│  │ search bar │    │ bar        │    │ results    │       │
│  │ + tips     │    │            │    │            │       │
│  └────────────┘    └────────────┘    └────────────┘       │
│       │                  │                 │               │
│       ▼                  ▼                 ▼               │
│  First-time         Autocomplete      Apply filters       │
│  walkthrough        suggestions       (type, date,        │
│  (optional)         appear as         author, dept)       │
│                     user types                            │
│                                            │               │
│                                            ▼               │
│                                     4. CONSUME             │
│                                     ┌────────────┐        │
│                                     │ Click to   │        │
│                                     │ open full  │        │
│                                     │ document   │        │
│                                     └────────────┘        │
│                                                            │
│  ──── ERROR PATHS ────                                     │
│                                                            │
│  Invalid query → Error + specific guidance                 │
│  No results    → Suggestions + "Did you mean?" + tips      │
│  Low relevance → "Try filters or rephrase" + suggestions   │
│  Rate limited  → "Too many queries, try again shortly"     │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 UX Design Principles (Industry Best Practices)

| Principle | Implementation | Source |
|---|---|---|
| **Single search bar** | One input field, accepting free-form natural language. No separate keyword/semantic modes. | Google, Glean, Algolia |
| **Rich result snippets** | Title, author, date, document type icon, relevance-highlighted excerpt. | Elastic, Coveo, Microsoft Search |
| **Faceted filtering** | Left sidebar with checkboxes: document type, date range, author, department. Show facet counts. | Coveo, Elastic, Amazon |
| **Zero-result recovery** | "Did you mean?", related searches, browse-by-category, query refinement tips. Never show a dead end. | Enterprise Knowledge, Algolia |
| **Sub-100ms autocomplete** | Suggestions appear as the user types, based on indexed content and popular queries. | Algolia, Elasticsearch |
| **First-time walkthrough** | Optional guided tour on first visit explaining search features and tips. | Deloitte brief requirement T4 |
| **Contextual guidance** | When queries return poor results, show specific suggestions for improvement. | Glean, Coveo |

### 5.3 Frontend Component Architecture (Next.js App Router)

The frontend is built with **Next.js (App Router)** using **TypeScript**, **Vercel AI SDK 6** (for streaming AI interactions and AI Elements), and **shadcn/ui** for the component library. The App Router provides server-side rendering, file-based routing, and React Server Components.

```
app/                              (Next.js App Router)
├── layout.tsx                    (root layout — shared nav, auth provider)
├── page.tsx                      (landing / search page)
├── search/
│   └── page.tsx                  (search results page with URL state)
│       ├── SearchBar             (shadcn/ui Input + AI Elements autocomplete)
│       │   ├── AutocompleteDropdown
│       │   └── SearchButton
│       ├── FilterPanel           (left sidebar)
│       │   ├── DocumentTypeFilter (shadcn/ui Checkbox group)
│       │   ├── DateRangeFilter    (shadcn/ui DatePicker)
│       │   ├── AuthorFilter       (shadcn/ui Combobox)
│       │   └── DepartmentFilter   (shadcn/ui Checkbox group)
│       ├── ResultsPanel          (main content)
│       │   ├── ResultCount + SortSelector
│       │   ├── ResultCard[]      (repeating — shadcn/ui Card)
│       │   │   ├── DocumentTypeIcon
│       │   │   ├── Title (linked)
│       │   │   ├── HighlightedSnippet
│       │   │   ├── MetadataRow (author, date, type)
│       │   │   └── RelevanceIndicator
│       │   ├── Pagination        (shadcn/ui Pagination)
│       │   └── ZeroResultsView   (conditional)
│       │       ├── SuggestedQueries
│       │       ├── SpellingCorrections
│       │       └── SearchTips
│       └── GuidancePanel         (contextual)
│           ├── FirstTimeWalkthrough (shadcn/ui Dialog, one-time)
│           ├── SearchTips          (shadcn/ui Collapsible)
│           └── QuerySuggestions
├── admin/
│   └── page.tsx                  (admin only — protected by NextAuth.js)
│       ├── DocumentUpload
│       ├── BoundaryConfig
│       └── AuditLogViewer
├── api/auth/[...nextauth]/
│   └── route.ts                  (NextAuth.js API route — Keycloak OIDC provider)
└── components/                   (shared UI components — shadcn/ui based)
```

---

## 6. NLP & Search Pipeline

### 6.1 Embedding Model: Qwen3-Embedding-0.6B

**Why Qwen3-Embedding-0.6B was selected:**

| Criteria | Qwen3-Embedding-0.6B | OpenAI text-embedding-3-large | Cohere embed-v4 |
|---|---|---|---|
| **Self-hosted** | Yes (Apache 2.0 license) | No (cloud API only) | No (cloud API only) |
| **Data privacy** | Full control — data never leaves your infrastructure | Data sent to OpenAI | Data sent to Cohere |
| **Parameters** | ~600M | Unknown (proprietary) | Unknown (proprietary) |
| **Dimensions** | 1024 | 3072 (adjustable) | 1024 |
| **Multilingual** | Strong multilingual support | Strong | Strong |
| **Cost** | Free (compute only) | $0.13/1M tokens | $0.10/1M tokens |
| **MMTEB Score** | ~70.58 | ~64.6 | ~65.2 |

**Decision rationale:** For a Deloitte enterprise system, data privacy is paramount. Qwen3-Embedding-0.6B allows all document content and queries to be processed on-premise without sending data to third-party APIs. At ~600M parameters, it is lightweight enough to self-host on modest hardware while delivering an MMTEB score of 70.58 — significantly outperforming both OpenAI (~64.6) and Cohere (~65.2). The Apache 2.0 license provides full flexibility for commercial and enterprise use. Unlike BGE-M3 (MMTEB ~63.0), which offered a unique sparse+multi-vector capability, Qwen3-Embedding-0.6B focuses on high-quality dense embeddings. The sparse/BM25 search capability is now handled separately by ParadeDB within PostgreSQL, making BGE-M3's multi-vector architecture unnecessary and allowing us to choose the strongest dense embedding model available.

### 6.2 Hybrid Retrieval Strategy

The search pipeline uses **parallel hybrid retrieval** — the most widely adopted pattern in enterprise search. Both search paths execute within the same PostgreSQL database, orchestrated by LlamaIndex:

**Path A — Semantic Search (PostgreSQL + pgvector):**
1. Query text → Qwen3-Embedding-0.6B → 1024-dim vector
2. pgvector cosine similarity search against the `embedding` column in the `chunks` table
3. Return top 50 results with similarity scores
4. SQL: `SELECT *, embedding <=> query_vector AS distance FROM chunks ORDER BY distance LIMIT 50`

**Path B — Keyword Search (PostgreSQL + ParadeDB):**
1. Query text → ParadeDB BM25 full-text search (pg_search extension)
2. BM25 scoring against `chunk_text` and document `title`
3. Return top 50 results with BM25 scores
4. SQL: `SELECT *, paradedb.score(id) FROM chunks WHERE chunk_text @@@ 'query' ORDER BY score DESC LIMIT 50`

**Why both?** Neither approach alone is sufficient:
- **Semantic search excels at**: understanding intent, handling vocabulary mismatch ("travel policy" matches "reimbursement guidelines"), paraphrase matching.
- **Keyword search excels at**: exact term matching (document titles, proper nouns, acronyms like "SOC 2" or "GAAP"), rare/specific terms that embedding models may under-represent.

**Why unified PostgreSQL?** Running both searches in the same database eliminates the need to synchronize metadata between two systems, removes network latency from external vector DB calls, and simplifies deployment to a single container. ParadeDB's BM25 implementation is purpose-built for PostgreSQL and outperforms the built-in `tsvector/tsquery` in relevance scoring.

Industry data: Elastic's testing shows hybrid search improves nDCG@10 by 12-18% over either method alone.

### 6.3 Reciprocal Rank Fusion (RRF)

**Formula:**
```
RRF_score(document) = Σ  1 / (k + rank_i(document))
                      i ∈ {semantic, keyword}
```

Where `k = 60` (standard constant, used by Elastic and Azure AI Search).

**Why RRF over weighted linear combination:**
- **Scale-independent**: BM25 scores might range from 0–15 while cosine similarity ranges from 0–1. RRF only uses rank positions, not raw scores, eliminating the need for normalization.
- **No tuning required**: Weighted combinations require a labeled dataset to optimize alpha. RRF works well out of the box.
- **Battle-tested**: Used in production by Elastic, Azure AI Search, OpenSearch, and Weaviate.

**Example calculation:**
| Document | Semantic Rank | Keyword Rank | RRF Score |
|---|---|---|---|
| Doc A | 1 | 3 | 1/(60+1) + 1/(60+3) = 0.01639 + 0.01587 = **0.03226** |
| Doc B | 5 | 1 | 1/(60+5) + 1/(60+1) = 0.01538 + 0.01639 = **0.03177** |
| Doc C | 2 | 10 | 1/(60+2) + 1/(60+10) = 0.01613 + 0.01429 = **0.03042** |

Doc A ranks highest because it performs well in both retrieval methods, which is the desired behavior — a document that both methods agree on is most likely relevant.

### 6.4 Reranking: Cohere Rerank 4

After RRF fusion produces an initial ranked list, the top candidates are passed through **Cohere Rerank 4** — a neural reranking model that uses cross-attention to jointly evaluate the query and each passage, producing a more accurate relevance score than the initial retrieval ranking.

**Why reranking?**
- **+33-40% accuracy improvement**: Reranking consistently improves nDCG@10 by 33-40% over retrieval-only pipelines (Superlinked, 2024).
- **Cross-attention vs. bi-encoder**: Initial retrieval uses bi-encoder embeddings (query and document encoded separately). Reranking uses cross-attention (query and document encoded together), which captures fine-grained token-level interactions that bi-encoders miss.
- **Practical latency**: Cohere Rerank 4 processes the top ~20-50 candidates in ~120ms — acceptable within our 2-second latency budget.

**Pipeline position:**
```
RRF Fusion (top ~100 candidates)
       │
       ▼
Cohere Rerank 4 (re-score top 50 using cross-attention)
       │
       ▼
Metadata Filtering & RBAC (apply access controls)
       │
       ▼
Return top 10 results to user
```

**Why Cohere Rerank 4 over alternatives:**

| Criteria | Cohere Rerank 4 | Cross-encoder (self-hosted) | No reranker |
|---|---|---|---|
| **Accuracy** | State-of-the-art | Good but requires GPU | Baseline |
| **Latency** | ~120ms for 50 docs | ~200-500ms | 0ms |
| **Operational cost** | API-based (simple) | Requires GPU hosting | None |
| **Maintenance** | Managed by Cohere | Self-maintained | None |

Note: Reranking is the one component where we use an external API. The data sent to Cohere for reranking consists only of query text and short passage snippets — not full documents — which limits the data exposure. The embedding model itself (Qwen3-Embedding-0.6B) remains fully self-hosted.

### 6.5 Intent Classification

The NLP Engine classifies each query into an intent category to optimize processing:

| Intent | Example Query | Search Behavior |
|---|---|---|
| **Navigational** | "Q4 healthcare deck" | Prioritize title/metadata matching. Weight keyword results higher. |
| **Informational** | "What are the billing thresholds for senior consultants?" | Prioritize chunk-level content matching. Weight semantic results higher. |
| **Exploratory** | "digital transformation trends" | Broader retrieval, show diverse results across document types. |

This is implemented as a lightweight classification layer (fine-tuned DistilBERT or similar) that runs in <10ms and adjusts the RRF weighting based on intent type.

### 6.6 Query Boundaries & Input Handling

Per the Deloitte brief (Technical Requirement T3), the system must define and enforce boundaries:

| Boundary | Rule | Implementation |
|---|---|---|
| **Language** | English only | Language detection via `langdetect` library; reject non-English |
| **Query length** | 1–500 characters | Validate before processing |
| **Content filtering** | Block profanity, offensive content | Blocklist + lightweight classifier |
| **PII detection** | Block queries containing SSN, credit card, etc. | Regex patterns for common PII formats |
| **Prompt injection** | Block attempts to manipulate NLP pipeline | Pattern matching + instruction-following guardrails |
| **Rate limiting** | Max 30 queries/minute per user | Token bucket algorithm in Rate Limiter middleware |
| **Graceful degradation** | Helpful error messages for all failure modes | Specific error messages per failure type with suggestions |

---

## 7. Security Architecture

### 7.1 Threat Model

Enterprise search systems face unique security challenges because they aggregate information from multiple sources, creating a high-value target:

| Threat | Risk Level | Attack Vector | Mitigation |
|---|---|---|---|
| **Prompt injection** | HIGH | Malicious instructions in queries to manipulate NLP | Input validation, pattern detection, privilege minimization |
| **RAG poisoning** | MEDIUM | Malicious content in indexed documents that manipulates search behavior | Document scanning at ingestion, canary tokens |
| **Data exfiltration** | HIGH | Crafted queries to extract sensitive information | Pre-filter RBAC, output filtering, audit logging |
| **Unauthorized access** | HIGH | Accessing documents above clearance level | Query-time RBAC enforcement (pre-filtering), fail-closed design |
| **Denial of service** | MEDIUM | Query flooding to overwhelm system | Rate limiting, request queuing, horizontal scaling |
| **Embedding inversion** | LOW | Reconstructing document text from stored embeddings | Access controls on PostgreSQL, no direct embedding column exposure via API |

### 7.2 Security Layers

```
┌─────────────────────────────────────────────────────┐
│  Layer 1: NETWORK SECURITY                          │
│  - HTTPS/TLS for all communications                 │
│  - Nginx reverse proxy at the edge                  │
│  - Docker network isolation between containers       │
└─────────────────────────────────────────────────────┘
          │
┌─────────────────────────────────────────────────────┐
│  Layer 2: AUTHENTICATION (Keycloak + NextAuth.js)   │
│  - Keycloak identity provider (Docker container)     │
│  - OIDC/SAML protocol support for enterprise SSO     │
│  - NextAuth.js (Auth.js) on the Next.js frontend     │
│  - JWT tokens issued by Keycloak, validated by       │
│    FastAPI backend                                   │
│  - Session management with secure, httpOnly cookies  │
└─────────────────────────────────────────────────────┘
          │
┌─────────────────────────────────────────────────────┐
│  Layer 3: AUTHORIZATION (RBAC)                      │
│  - Role hierarchy: employee, admin                   │
│  - Document-level access tags (public, internal,     │
│    confidential, restricted)                         │
│  - Pre-filtering: RBAC applied BEFORE retrieval      │
│    results are assembled (not after)                 │
└─────────────────────────────────────────────────────┘
          │
┌─────────────────────────────────────────────────────┐
│  Layer 4: INPUT VALIDATION                          │
│  - Query sanitization (XSS, SQL injection)           │
│  - PII detection and blocking                        │
│  - Prompt injection pattern detection                │
│  - Content filtering (profanity, offensive content)  │
│  - Length and language validation                     │
└─────────────────────────────────────────────────────┘
          │
┌─────────────────────────────────────────────────────┐
│  Layer 5: AUDIT & MONITORING                        │
│  - Every query logged with user_id, timestamp,       │
│    query text, result count, selected document       │
│  - Admin access to audit log viewer                  │
│  - Anomaly detection on query patterns               │
└─────────────────────────────────────────────────────┘
```

### 7.3 Pre-Filtering vs. Post-Filtering RBAC

**This project uses pre-filtering** — access controls are applied during the retrieval step, not after.

| Approach | How It Works | Pros | Cons |
|---|---|---|---|
| **Pre-filtering** (our approach) | Include `access_level` in PostgreSQL WHERE clauses for both pgvector similarity search and ParadeDB BM25 search. Unauthorized documents are never retrieved. | User never sees unauthorized results, even in intermediate processing. More secure. | May reduce recall if access controls are too restrictive. |
| **Post-filtering** | Retrieve top-K results from all documents, then filter out unauthorized ones. | Higher recall; simpler to implement. | User may see fewer results than expected. Metadata about unauthorized docs may leak. |

Glean, Microsoft Search, and Azure AI Search all use pre-filtering for enterprise deployments where compliance is critical.

### 7.4 Compliance Considerations

| Standard | Relevance | How We Address It |
|---|---|---|
| **SOC 2** | De facto requirement for enterprise B2B AI | Comprehensive audit logging; access controls; encryption at rest and in transit; documented security practices |
| **GDPR** | Applies if any EU employee data is processed | Right to erasure: ability to remove user's data from PostgreSQL (metadata, vectors, and logs); data minimization in logging |
| **Deloitte Internal Policy** | Assumed: strict data handling requirements | On-premise/self-hosted embedding model (Qwen3-Embedding-0.6B); document content never sent to third-party APIs (Cohere Rerank receives only short passage snippets); fail-closed authorization |

---

## 8. Deployment & Infrastructure

### 8.1 Container Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  DOCKER HOST (Cloud Server / On-Premise)                    │
│                                                             │
│  ┌─────────────────────┐    ┌─────────────────────────────┐│
│  │  FRONTEND CONTAINER │    │  BACKEND CONTAINER          ││
│  │                     │    │                             ││
│  │  Node.js 20+        │    │  Python 3.11+              ││
│  │  ├─ Next.js (App    │    │  ├─ FastAPI (Uvicorn ASGI) ││
│  │  │  Router) + SSR   │    │  ├─ LlamaIndex (retrieval  ││
│  │  ├─ NextAuth.js     │    │  │   orchestration)         ││
│  │  │  (Keycloak OIDC) │    │  ├─ NLP Engine              ││
│  │  └─ Vercel AI SDK 6 │    │  │  ├─ Qwen3-Embedding-    ││
│  │                     │    │  │  │  0.6B model           ││
│  │  Port: 3000         │    │  │  └─ Intent classifier    ││
│  │                     │    │  ├─ Input Validator         ││
│  └─────────────────────┘    │  ├─ Ranking Service         ││
│                              │  │  └─ Cohere Rerank 4     ││
│  ┌─────────────────────┐    │  └─ Ingestion Pipeline     ││
│  │  KEYCLOAK CONTAINER │    │     └─ Docling (IBM)        ││
│  │                     │    │                             ││
│  │  Keycloak 24+       │    │  Port: 8000 (internal)     ││
│  │  ├─ Identity        │    └─────────────────────────────┘│
│  │  │  provider        │                                    │
│  │  ├─ OIDC/SAML       │    ┌─────────────────────────────┐│
│  │  │  endpoints       │    │  DATABASE CONTAINER         ││
│  │  └─ User federation │    │                             ││
│  │                     │    │  PostgreSQL 16              ││
│  │  Port: 8080         │    │  + pgvector extension       ││
│  │  (internal)         │    │  + ParadeDB extension       ││
│  └─────────────────────┘    │                             ││
│                              │  ├─ Metadata store          ││
│  ┌─────────────────────┐    │  ├─ Vector store (pgvector) ││
│  │  NGINX CONTAINER    │    │  ├─ BM25 search (ParadeDB)  ││
│  │                     │    │  ├─ Audit logs              ││
│  │  Nginx 1.25+        │    │  └─ User/role data          ││
│  │  ├─ Reverse proxy   │    │                             ││
│  │  ├─ HTTPS           │    │  Port: 5432 (internal)     ││
│  │  │  termination     │    └─────────────────────────────┘│
│  │  └─ Route to        │                                    │
│  │     frontend/API    │    ┌─────────────────────────────┐│
│  │                     │    │  EXTERNAL API               ││
│  │  Port: 80/443       │    │                             ││
│  └─────────────────────┘    │  Cohere Rerank 4 API        ││
│                              │  (reranking only — no       ││
│                              │   document content sent)    ││
│                              └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Docker Compose Overview

The system deploys with `docker-compose` for local development and can be orchestrated with Kubernetes for production scaling. Five containers:

1. **frontend** — Node.js running Next.js (App Router) with SSR; NextAuth.js handles authentication via Keycloak OIDC.
2. **backend** — FastAPI on Uvicorn; loads the Qwen3-Embedding-0.6B model at startup; LlamaIndex orchestrates the retrieval pipeline; connects to PostgreSQL for all data operations.
3. **db** — PostgreSQL 16 with pgvector and ParadeDB extensions; persistent volume; initialized with schema migrations on first run.
4. **keycloak** — Keycloak 24+ identity provider; provides OIDC/SAML authentication endpoints; manages user federation and roles.
5. **nginx** — Nginx 1.25+ reverse proxy; handles HTTPS termination and routes requests to frontend and API.

**Why Docker?** Per the proposal: "Reproducible environments and cloud-ready." Docker ensures every team member runs an identical stack, and the same containers deploy to any cloud provider.

### 8.3 Communication Protocols

| Connection | Protocol | Port | Encryption |
|---|---|---|---|
| Browser → Nginx | HTTPS | 443 | TLS 1.3 |
| Nginx → Next.js Frontend | HTTP (internal Docker network) | 3000 | Docker network isolation |
| Next.js Frontend → FastAPI Backend | HTTP (internal Docker network) | 8000 | Docker network isolation |
| Next.js Frontend → Keycloak | HTTP (internal Docker network) | 8080 | Docker network isolation |
| Backend → PostgreSQL (pgvector + ParadeDB) | PostgreSQL wire protocol | 5432 | Docker network isolation |
| Backend → Cohere Rerank 4 | HTTPS (REST API) | 443 | TLS in transit |
| Backend → Qwen3-Embedding-0.6B | In-process (loaded in same container) | N/A | N/A |

---

## 9. Performance & Scalability

### 9.1 Performance Targets

| Metric | Target | Industry Benchmark |
|---|---|---|
| **Search response time (p95)** | < 2 seconds | Glean: ~1.5s; Elastic: < 500ms for hybrid |
| **Autocomplete response** | < 100ms | Algolia: < 50ms |
| **Document ingestion** | < 30 seconds per document | Varies by document size |
| **Concurrent users** | 50+ simultaneous queries | Prototype scope |
| **Availability** | 99% uptime during demo periods | Prototype scope |

### 9.2 Latency Budget (2-Second Target)

| Step | Estimated Latency | Notes |
|---|---|---|
| Input validation | ~5ms | String operations, regex |
| Intent classification | ~10ms | Lightweight model inference |
| Embedding generation | ~50ms | Qwen3-Embedding-0.6B single query |
| Semantic search (pgvector) | ~80ms | In-database HNSW index, no network hop |
| Keyword search (ParadeDB BM25) | ~50ms | In-database BM25 with GIN index |
| **Retrieval subtotal** | ~80ms | Parallel — max of semantic/keyword |
| RRF fusion | ~10ms | In-memory ranking |
| **Reranking (Cohere Rerank 4)** | **~120ms** | Neural reranking of top 50 candidates |
| Metadata filtering & RBAC | ~5ms | SQL WHERE clause filtering |
| Result assembly | ~10ms | JSON serialization |
| Network overhead (round trips) | ~100ms | Browser ↔ Frontend ↔ Backend |
| **Total estimated** | **~390ms** | Well within 2s budget |

This budget leaves significant headroom for:
- Network variability
- Cold-start scenarios
- The reranking step adds ~120ms but provides a +33-40% accuracy improvement, a worthwhile tradeoff within our 2-second budget

### 9.3 Caching Strategy

| Cache Layer | What It Caches | TTL | Technology |
|---|---|---|---|
| **Browser cache** | Static assets (JS, CSS, images) | Long-lived (hashed filenames) | HTTP cache headers |
| **Application cache** | Popular query results | 5–15 minutes | In-memory (Python dict) or Redis |
| **Embedding cache** | Query embeddings | Session-length | In-memory LRU cache |

For the prototype, in-memory caching is sufficient. Production would use Redis for distributed caching with semantic similarity matching.

---

## 10. Technology Stack Justification

| Layer | Technology | Why This Choice |
|---|---|---|
| **Frontend** | Next.js (App Router) + TypeScript + Vercel AI SDK 6 | App Router provides SSR, file-based routing, and React Server Components. Vercel AI SDK 6 provides AI Elements for streaming AI interactions. shadcn/ui provides accessible, customizable UI components. TypeScript provides type safety for complex state management. |
| **Frontend Auth** | NextAuth.js (Auth.js) | Seamless integration with Next.js App Router. Supports Keycloak OIDC provider out of the box. Handles session management, JWT validation, and CSRF protection. |
| **Identity Provider** | Keycloak (Docker container) | Open-source identity provider with OIDC/SAML support. Enterprise-grade user federation, role management, and SSO. Runs as a Docker container alongside the application. |
| **Backend** | Python + FastAPI | FastAPI is the de facto standard for AI-integrated Python applications. Native async support critical for parallel retrieval. Pydantic models provide request/response validation. Python ecosystem has the best NLP/ML library support. |
| **RAG Framework** | LlamaIndex | Orchestrates the retrieval pipeline (embedding, search, reranking). Provides abstractions for hybrid search, query engines, and document ingestion. Integrates with pgvector, ParadeDB, and Cohere Rerank. |
| **ASGI Server** | Uvicorn | High-performance ASGI server for FastAPI. Supports async concurrency out of the box. Production-ready with Gunicorn as process manager. |
| **Embedding Model** | Qwen3-Embedding-0.6B | Self-hosted (Apache 2.0 license) — Deloitte data stays on-premise. ~600M params, 1024 dimensions. MMTEB score 70.58, outperforming OpenAI and Cohere. |
| **Reranker** | Cohere Rerank 4 | Neural reranking with cross-attention for +33-40% accuracy improvement. ~120ms latency for top 50 candidates. Only short passage snippets sent to API. |
| **Document Parser** | Docling (IBM) | Unified document parsing with 97.9% accuracy on complex table extraction. Handles PDF, DOCX, PPTX, images, and HTML. |
| **Database** | PostgreSQL 16 + pgvector + ParadeDB | Unified store for vectors (pgvector), BM25 keyword search (ParadeDB), metadata, and audit logs. Eliminates external vector DB, removes duplicate metadata, provides ACID guarantees. HNSW index for vector similarity search. |
| **Reverse Proxy** | Nginx | Proxies requests to Next.js frontend and FastAPI backend. Handles HTTPS termination. Battle-tested in enterprise deployments. |
| **Containerization** | Docker + Docker Compose | Reproducible environments. Every team member runs identical stack. Cloud-portable. |
| **Version Control** | GitHub | Collaborative development, code review, CI/CD integration. |

### 10.1 Alternative Technologies Considered

| Decision | Chosen | Alternatives Considered | Why We Chose What We Did |
|---|---|---|---|
| Vector + Search DB | PostgreSQL + pgvector + ParadeDB | Pinecone, Qdrant, Weaviate, Elasticsearch | Unified store eliminates duplicate metadata, removes network hops for vector search, simplifies deployment to one DB container. pgvector HNSW performance is sufficient at our scale. ParadeDB provides superior BM25 scoring over PostgreSQL's built-in tsvector/tsquery. |
| Embedding | Qwen3-Embedding-0.6B | BGE-M3, OpenAI, Cohere | Qwen3-Embedding-0.6B: self-hosted (Apache 2.0), MMTEB 70.58 vs BGE-M3's 63.0. BGE-M3's sparse+multi-vector capability no longer needed since ParadeDB handles BM25 separately. No API costs. |
| Reranker | Cohere Rerank 4 | Self-hosted cross-encoder, no reranker | Cohere Rerank 4: +33-40% accuracy improvement. API-based simplicity vs. GPU hosting overhead for self-hosted cross-encoder. Only short snippets sent to API. |
| Document Parser | Docling (IBM) | Unstructured.io, LangChain loaders, PyMuPDF | Docling: 97.9% accuracy on complex table extraction. Unified parser for all formats. Open-source (MIT). |
| Frontend | Next.js (App Router) | React SPA, Remix, SvelteKit | Next.js App Router: SSR for SEO and performance, file-based routing, React Server Components. Vercel AI SDK 6 provides AI Elements. Mature ecosystem. |
| Auth | Keycloak + NextAuth.js | Auth0, Firebase Auth, custom JWT | Keycloak: open-source, self-hosted, enterprise-grade OIDC/SAML. NextAuth.js: native Next.js integration. No vendor lock-in. |
| RAG Framework | LlamaIndex | LangChain, Haystack, custom | LlamaIndex: purpose-built for retrieval, strong pgvector integration, supports hybrid search and reranking out of the box. |
| Backend | FastAPI | Django, Flask, Express.js | FastAPI: native async, automatic OpenAPI docs, Pydantic validation. Best for AI workloads. |
| Search fusion | RRF | Weighted combination, DBSF | RRF: no tuning required, scale-independent, industry standard. |

---

## 11. Use Case Deep Dive

### 11.1 Use Cases Summary

| ID | Name | Primary Actor | Trigger | Key Technical Component |
|---|---|---|---|---|
| UC1 | Search for Resources by Name or Topic | Deloitte Employee | Need to find a known resource | Full hybrid retrieval pipeline |
| UC2 | Search for Information Within Documents | Deloitte Employee | Need a specific fact/data point | Chunk-level semantic matching + passage highlighting |
| UC3 | Filter and Refine Search Results | Deloitte Employee | Initial results too broad | Metadata filtering with faceted UI |
| UC4 | Ingest and Index Documents | System Administrator | New resources available | Document ingestion pipeline |
| UC5 | Manage Query Boundaries | System Administrator | Security policy update | Admin configuration interface |

### 11.2 Use Case Relationships

- **UC1 → UC2**: Both use the same hybrid retrieval pipeline, but UC2 emphasizes chunk-level content matching and passage highlighting rather than document-level matching.
- **UC1 → UC3** and **UC2 → UC3**: UC3 extends both search use cases as an optional post-search step (applying filters does not require a new query).
- **UC4 ↔ UC1/UC2**: UC4 populates the data stores that UC1 and UC2 search against.
- **UC5 ↔ all**: UC5 configures the rules that govern query validation in UC1 and UC2.

### 11.3 Use Case Specification (UC1 — Short Form Template)

*Already detailed in the current Software Engineering Draft. The specification covers:*

- **Scope**: Deloitte AI-Driven Search Engine Web Application
- **Level**: User Goal
- **Primary Actor**: Deloitte Employee
- **Stakeholders**: Employee (find resources), Admin (enforce boundaries), Management (improve productivity)
- **Preconditions**: User has access; database is populated
- **Main Success Scenario**: 10-step flow from query entry through validation, intent classification, embedding, parallel retrieval, RRF fusion, result display, and logging
- **Extensions**: 4 alternate flows (validation failure, zero results, low relevance, rate limiting)
- **Special Requirements**: <2s p95 latency, concurrent user support, audit logging

---

## 12. Diagram Descriptions & Rationale

### 12.1 Use Case Diagram

**What it shows**: Two actors (Deloitte Employee, System Administrator) and five use cases with extend relationships showing how search, filtering, and content search relate to each other.

**Design rationale**: The `extends` relationship was chosen over `includes` because filtering and within-document search are optional extensions of the primary search use case, not mandatory steps. An employee can search (UC1) without ever filtering (UC3) or doing within-document search (UC2).

### 12.2 Activity Diagram

**What it shows**: The complete search workflow from query entry through result display, including all decision points (validation, result found?, user actions).

**Design rationale**: The parallel paths (BM25 + semantic search) are explicitly shown as concurrent activities because this parallelism is a core architectural decision that directly impacts latency. The activity diagram captures the three possible user outcomes after results display: select a result, apply filters, or refine the query — matching the actual UI interaction model.

### 12.3 Sequence Diagram

**What it shows**: Object-level message passing between Next.js Frontend, FastAPI Backend, Input Validator, NLP Engine (LlamaIndex), PostgreSQL (pgvector + ParadeDB), Cohere Reranker, and Ranking Service during a search request.

**Design rationale**: The `alt` block separating validation failure from success is critical — it shows the system's fail-fast behavior. The `par` block for parallel retrieval demonstrates the concurrent architecture (both pgvector and ParadeDB queries against the same PostgreSQL instance). Named method calls (`validate()`, `classify_intent()`, `generate_embedding()`, `vector_search()`, `bm25_search()`, `rrf_fusion()`, `rerank()`, `log_query()`) provide specificity beyond what a generic sequence diagram would show.

### 12.4 Component Diagram

**What it shows**: Four architectural layers with components and their dependencies.

**Design rationale**: The separation into Frontend/API/Processing/Data layers directly reflects the deployment architecture (each layer maps to a container or service). The External dependencies (Qwen3-Embedding-0.6B model, Cohere Rerank 4, Document Sources) are separated because they represent components outside the core system boundary but critical to its operation.

### 12.5 Deployment Diagram

**What it shows**: Physical topology — client browser, five Docker containers (Next.js frontend, FastAPI backend, PostgreSQL with pgvector/ParadeDB, Keycloak, Nginx), and Cohere Rerank 4 external API with communication protocols.

**Design rationale**: The five-container approach (nginx, frontend, backend, database, keycloak) provides proper separation of concerns while keeping all core services self-hosted. The NLP Engine is co-located with the backend (same container) rather than in a separate container to minimize inference latency — the Qwen3-Embedding-0.6B model is loaded once at startup and serves requests in-process, avoiding network overhead for every query. The unified PostgreSQL container (with pgvector and ParadeDB extensions) replaces the previous external vector database service, simplifying the deployment topology.

---

## 13. Gap Analysis: Current Draft vs. This Report

### 13.1 What the Current Draft Does Well

| Strength | Assessment |
|---|---|
| **All 8 required deliverables present** | Exceeds both past examples (DataCommunique and CommerceonRails each had missing items) |
| **5 use cases listed and described** | Assignment asks for 3-5; past examples only had 1 each |
| **Full short-form specification** | Follows Cockburn template with all fields (Scope, Level, Actor, Stakeholders, Preconditions, Main Success, Extensions, Special Requirements) |
| **Detailed descriptions for every diagram** | Each diagram has a substantive paragraph explaining what it shows and why — stronger than both past examples |
| **Technical specificity** | Names actual technologies, methods, and data flows throughout |
| **All 5 diagram types present** | Use Case, Activity, Sequence, Component, Deployment — all required |

### 13.2 Areas for Enhancement

| Area | Current State | Recommended Enhancement | Priority |
|---|---|---|---|
| **Software Design intro section** | Good overview but lacks industry context | Add 1-2 paragraphs on why hybrid search architecture was chosen (cite Elastic, Glean as precedents). This is what the assignment calls "describe Software Design and Engineering based on lecture and web research." | HIGH |
| **Data flow narrative** | Implicit in diagrams but not explicitly documented | Add a "Data Flow" subsection describing the query-time pipeline and ingestion pipeline in prose (from Section 4 of this report). This fills the "architecture, data flow, user flow" gap you identified. | HIGH |
| **Data model** | Not included | Add the PostgreSQL schema with pgvector and ParadeDB extensions (from Section 4.3). Shows the professor you've thought through data persistence. | MEDIUM |
| **Security narrative** | RBAC mentioned in diagrams; not expanded | Add a "Security Considerations" subsection with the threat model and security layers (from Section 7). This directly addresses Deloitte's Deliverable 2 and Technical Requirement T3. | HIGH |
| **Technology justification** | Technologies are named but rationale is minimal | Add a "Technology Selection" table with brief justifications for each choice (from Section 10). Shows critical thinking. | MEDIUM |
| **Performance targets** | Mentioned in special requirements (< 2s) | Add a brief "Performance" subsection with the latency budget breakdown (from Section 9.2). Makes the 2s target credible. | LOW |
| **UX/User flow narrative** | Implicit in activity diagram | Consider adding a brief "User Experience" subsection describing the user journey (from Section 5.1). Aligns with Deloitte's T4 (user guidance). | LOW |
| **«extends» arrow labels** | Missing guillemets in some places | Ensure all UML relationship labels use proper notation (`«extends»`). Minor formatting. | LOW |

### 13.3 Compliance with Assignment Requirements

| Requirement | Status | Notes |
|---|---|---|
| a. Software Design and Engineering document (Word .docx) | **NEEDS FINALIZATION** | Draft is in Markdown; needs conversion to .docx with rendered diagrams |
| b. 3-5 Use Cases listed and described | **COMPLETE** | 5 use cases, each with description, actors, and trigger |
| c. Use Case Specification (short form template) | **COMPLETE** | UC1 fully specified with all template fields |
| d. Use Case Diagram | **COMPLETE** | Shows all 5 use cases, 2 actors, extends relationships |
| e. Activity Diagram (created and described) | **COMPLETE** | Full workflow with description paragraph |
| f. Sequence Diagram (created and described) | **COMPLETE** | Object-level interactions with description paragraph |
| g. Component Diagram (created and described) | **COMPLETE** | Four-layer architecture with description paragraph |
| h. Deployment Diagram (created and described) | **COMPLETE** | Docker topology with description paragraph |

### 13.4 Recommended Priority Actions

1. **HIGH**: Enrich Section 1 (Introduction) with 1-2 paragraphs on the software design approach and industry context for the architectural decisions.
2. **HIGH**: Add a "Data Flow" subsection (can be Section 3.5 or similar) describing query-time and ingestion-time data flows.
3. **HIGH**: Add a "Security Considerations" subsection covering the threat model, security layers, and RBAC approach.
4. **MEDIUM**: Add a "Data Model" subsection with the unified PostgreSQL schema (pgvector + ParadeDB).
5. **MEDIUM**: Add a "Technology Selection" table with justifications.
6. **LOW**: Add performance targets with latency budget.
7. **FINAL**: Convert .md to .docx with rendered diagram images (PNG from Mermaid).

---

## 14. References

### Enterprise Search Platforms
- Glean. "How Glean Search Works." https://www.glean.com/resources/guides/how-glean-search-works
- Elastic. "Introducing Elastic Learned Sparse Encoder (ELSER)." https://www.elastic.co/search-labs/blog/introducing-elastic-learned-sparse-encoder-elser
- Microsoft. "Semantic Indexing for Microsoft 365 Copilot." https://learn.microsoft.com/en-us/microsoftsearch/semantic-index-for-copilot
- Algolia. "What is Enterprise Search?" https://www.algolia.com/blog/product/what-is-enterprise-search

### Hybrid Search & Ranking
- Azure. "Hybrid Search Scoring." https://learn.microsoft.com/en-us/azure/search/hybrid-search-ranking
- Weaviate. "Hybrid Search Explained." https://weaviate.io/blog/hybrid-search-explained
- OpenSearch. "Introducing Reciprocal Rank Fusion." https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search

### RAG & Retrieval
- Applied AI. "Enterprise RAG Architecture Guide." https://www.applied-ai.com/briefings/enterprise-rag-architecture/
- Elastic. "Advanced RAG Techniques." https://www.elastic.co/search-labs/blog/advanced-rag-techniques-part-1
- Superlinked. "Optimizing RAG with Hybrid Search & Reranking." https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking

### Embedding Models
- Qwen. "Qwen3-Embedding-0.6B on HuggingFace." https://huggingface.co/Qwen/Qwen3-Embedding-0.6B
- BAAI. "BGE-M3 on HuggingFace." https://huggingface.co/BAAI/bge-m3
- MTEB Leaderboard. https://huggingface.co/spaces/mteb/leaderboard

### Reranking
- Cohere. "Rerank 4." https://cohere.com/rerank
- Superlinked. "Optimizing RAG with Hybrid Search & Reranking." https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking

### Chunking & Document Processing
- IBM. "Docling — Document Parsing Library." https://github.com/DS4SD/docling
- Firecrawl. "Best Chunking Strategies for RAG 2025." https://www.firecrawl.dev/blog/best-chunking-strategies-rag
- Weaviate. "Chunking Strategies for RAG." https://weaviate.io/blog/chunking-strategies-for-rag

### Vector Search & Database
- pgvector. "Open-source vector similarity search for PostgreSQL." https://github.com/pgvector/pgvector
- ParadeDB. "PostgreSQL for Search and Analytics." https://www.paradedb.com/
- LlamaIndex. "LlamaIndex Documentation." https://docs.llamaindex.ai/

### Authentication & Identity
- Keycloak. "Open Source Identity and Access Management." https://www.keycloak.org/
- NextAuth.js. "Authentication for Next.js." https://next-auth.js.org/

### Frontend
- Next.js. "The React Framework for the Web." https://nextjs.org/
- Vercel. "AI SDK." https://sdk.vercel.ai/
- shadcn/ui. "Re-usable components built with Radix UI and Tailwind CSS." https://ui.shadcn.com/

### Security
- OWASP. "LLM Prompt Injection Prevention Cheat Sheet." https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html
- Azure. "Document-Level Security in Azure AI Search." https://azureaggregator.wordpress.com/2025/05/30/announcing-enterprise-grade-microsoft-entra-based-document-level-security-in-azure-ai-search/

### UX
- Enterprise Knowledge. "Search UX Best Practices." https://enterprise-knowledge.com/search-ux-best-practices-part-1-user-input/
- SearchBlox. "Best Practices for Enterprise Search UX." https://www.searchblox.com/best-practices-for-enterprise-search-user-experience-ux

### Performance
- Redis. "Semantic Caching Guide." https://redis.io/blog/how-to-cache-semantic-search/
- Glean. "2025 Search Tool Benchmark." https://www.glean.com/blog/2025-search-tool-benchmark-key-metrics-to-evaluate-accuracy-and-speed

### Project-Specific Sources
- Microsoft. "Work Trend Index: Will AI Fix Work?" May 2023.
- APQC. "Fixing Process & Knowledge Productivity Problems." 2021.
- SPI Research. "Professional Services Maturity Benchmark Report." 2025.
- Slite. "Enterprise Search Survey Report." 2025.
