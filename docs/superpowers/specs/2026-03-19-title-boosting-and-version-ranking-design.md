# Title Boosting & Version-Aware Ranking

**Date:** 2026-03-19
**Status:** Draft
**Scope:** Backend search pipeline, database schema, frontend filter UI

## Problem Statement

Two ranking gaps in the current hybrid search pipeline:

1. **No title signal.** All search operates at the chunk level. A document whose title matches the query has no ranking advantage over a document that happens to contain matching text on page 47. Users searching "remote work policy" expect the document *named* "Remote Work Policy" to rank highly, even if another document's buried content is also relevant.

2. **No version awareness.** Multiple versions of the same document (e.g., `Remote_Work_Policy.docx` and `Remote_Work_Policy_v2.docx`) are treated as completely independent. There is no mechanism to prefer newer versions or filter out superseded ones.

## Design Overview

### Title Boosting: Third RRF Signal

Add title similarity as a third independent retrieval path alongside semantic chunk search and BM25 chunk search. Title results feed into the existing RRF merge with a configurable weight multiplier.

```
Query -> Embed -> Parallel retrieval:
  |-- pgvector cosine similarity on chunks (existing)
  |-- ParadeDB BM25 on chunks (existing)
  |-- pgvector cosine similarity on title embeddings (NEW)
-> Weighted RRF merge (3 lists) -> Batch doc fetch -> Cohere Rerank -> Version filter -> Results
```

Title match acts as a strong but not absolute boost. A deeply relevant content match in another document can still outrank a title match if the content relevance is strong enough. The weight is tunable via `TITLE_BOOST_WEIGHT` (default `1.5`).

### Version-Aware Ranking: Document Groups

Documents are linked into version groups at ingestion time via filename convention detection. A `document_group` column stores the normalized base title, and a `version` integer tracks the revision number. A frontend toggle ("Show latest versions only", on by default) filters results to only the newest version per group.

## Database Schema Changes

### Documents table: add versioning columns

```sql
ALTER TABLE documents ADD COLUMN document_group TEXT;
ALTER TABLE documents ADD COLUMN version INTEGER DEFAULT 1 CHECK (version >= 1);

CREATE INDEX idx_documents_document_group ON documents(document_group);
ALTER TABLE documents ADD CONSTRAINT uq_document_group_version UNIQUE (document_group, version);
```

- `document_group`: normalized base title linking all versions (e.g., `"remote work policy"` for both v1 and v2)
- `version`: integer starting at 1, extracted from `_v(\d+)` filename suffix
- Unique constraint prevents duplicate version numbers within a group

### New table: document_title_embeddings

```sql
CREATE TABLE IF NOT EXISTS document_title_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    title_text TEXT NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_title_embeddings_vector
    ON document_title_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);
```

**Why a separate table:**
- Keeps `documents` clean as a metadata table -- no 1024-dim vector bloating every row fetch (admin UI, document listings)
- HNSW index lives on a compact, dedicated table -- faster index builds (tens of rows vs thousands of chunks)
- Independently tunable: can swap embedding model, dimensions, or index strategy for titles without touching chunk infrastructure
- `ON DELETE CASCADE` keeps it maintenance-free

### ORM additions to db.py

- Add `document_group: Mapped[str | None]` and `version: Mapped[int]` to `Document` model
- New `DocumentTitleEmbedding` model class with `relationship` back to `Document`

### init.sql updates

Add both the new columns and new table to `init.sql` so fresh database creation includes them.

## Ingestion Pipeline Changes

### Version detection from filename

In `ingest_document()`, before creating the document record:

```python
import re

def _extract_version_info(filename: str) -> tuple[str, int]:
    """Extract document_group and version from filename.

    'Remote_Work_Policy_v2.docx' -> ('remote work policy', 2)
    'Acceptable_Use_Policy.pdf'  -> ('acceptable use policy', 1)
    """
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

### Title embedding generation

After creating the document record and flushing to get `doc.id`, embed the title string and insert into `document_title_embeddings`. Reuses the existing `generate_embedding()` function -- one additional embedding call per document (not per chunk).

### BM25 index creation fix

Replace the current try/except/rollback pattern with a check-before-create:

```python
async def _ensure_bm25_index(db: AsyncSession):
    result = await db.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_chunks_bm25'"
    ))
    if result.fetchone() is None:
        await db.execute(text("""
            CALL paradedb.create_bm25(
                index_name => 'idx_chunks_bm25',
                table_name => 'document_chunks',
                key_field => 'id',
                text_fields => paradedb.field('content')
            )
        """))
        await db.commit()
```

## Search Pipeline Changes

### Title similarity query (third signal)

```sql
SELECT dte.document_id,
       1 - (dte.embedding <=> CAST(:embedding AS vector)) AS score
FROM document_title_embeddings dte
JOIN documents d ON dte.document_id = d.id
WHERE d.access_level IN (:access_levels)  -- parameterized, not f-string
ORDER BY dte.embedding <=> CAST(:embedding AS vector)
LIMIT :top_k
```

Runs with the same query embedding used for chunk semantic search -- no extra embedding API call.

### Weighted RRF merge

Extend `_rrf_merge` to accept three lists with a title weight:

```python
def _rrf_merge(semantic_rows, bm25_rows, title_rows, k=60, title_weight=1.5):
    scores = {}

    for rank, row in enumerate(semantic_rows):
        _add_chunk_score(scores, row, 1.0 / (k + rank + 1))

    for rank, row in enumerate(bm25_rows):
        _add_chunk_score(scores, row, 1.0 / (k + rank + 1))

    # Title results are document-level, not chunk-level.
    # Boost ALL chunks belonging to title-matched documents.
    title_doc_scores = {}
    for rank, row in enumerate(title_rows):
        title_doc_scores[str(row.document_id)] = title_weight * (1.0 / (k + rank + 1))

    for chunk_id, chunk_data in scores.items():
        doc_id = str(chunk_data["document_id"])
        if doc_id in title_doc_scores:
            chunk_data["rrf_score"] += title_doc_scores[doc_id]

    # Also add title-matched docs that had no chunk hits
    # (edge case: title matches but no chunk content matched)
    # These get injected with a synthetic entry using the title as snippet.

    return sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
```

**Key insight:** Title search returns document-level results, not chunks. The RRF merge boosts all chunks belonging to a title-matched document. This means a document with both a title match AND a strong content match gets a double boost -- which is the correct behavior (it's the most relevant document on both signals).

### Fix N+1 query -> batch fetch

After RRF merge and reranking, collect all unique `document_id` values and fetch in one query:

```python
doc_ids = list({chunk["document_id"] for chunk in top_chunks})
doc_sql = text("SELECT * FROM documents WHERE id = ANY(:doc_ids)")
doc_rows = (await db.execute(doc_sql, {"doc_ids": doc_ids})).fetchall()
doc_map = {row.id: row for row in doc_rows}
```

Reduces worst-case 10 round-trips to 1.

### Fix SQL injection pattern

Replace f-string access_filter with parameterized IN clause:

```python
access_levels = _get_access_levels(user_role)
access_placeholders = ", ".join(f":access_{i}" for i in range(len(access_levels)))
access_params = {f"access_{i}": level for i, level in enumerate(access_levels)}
```

Apply to all three queries (semantic, BM25, title).

### Version filtering

Post-rerank filter, controlled by `show_latest_only` parameter:

```python
if show_latest_only:
    latest_versions = {}  # document_group -> max version seen
    for result in results:
        group = result.document_group
        if group is None:
            continue  # ungrouped docs always shown
        if group not in latest_versions or result.version > latest_versions[group]:
            latest_versions[group] = result.version

    results = [
        r for r in results
        if r.document_group is None or r.version == latest_versions[r.document_group]
    ]
```

Applied after reranking so it does not affect retrieval quality -- it only filters the final output.

### Wire up filters parameter

The existing `filters` parameter on `SearchRequest` is accepted but currently ignored. Implement category filtering in all three SQL queries by adding `AND d.category = :category` when `filters.get("category")` is present.

## API Changes

### SearchRequest schema

```python
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: dict | None = None
    top_k: int = Field(default=10, ge=1, le=50)
    show_latest_only: bool = True  # NEW
```

### SearchResultItem schema

```python
class SearchResultItem(BaseModel):
    document_id: UUID
    title: str
    author: str | None
    doc_type: str
    category: str
    access_level: str
    snippet: str
    score: float
    page_count: int | None
    created_date: datetime | None
    version: int | None = None           # NEW
    document_group: str | None = None     # NEW
```

### Config additions

```python
TITLE_BOOST_WEIGHT: float = 1.5  # RRF weight multiplier for title signal
```

## Frontend Changes

### Search results page

- Add toggle switch: "Show latest versions only" (on by default)
- Pass `show_latest_only` parameter to API via `lib/api.ts`
- Display version badge on results when `version > 1` (e.g., small "v2" tag next to the title)
- When `show_latest_only` is off, visually distinguish older versions (muted styling or "Older version" label)

### API client

Update `lib/api.ts` search function to include `show_latest_only` in the request body.

## DB Round-Trip Summary

| Step | Current | Proposed |
|------|---------|----------|
| Semantic chunk search | 1 query | 1 query |
| BM25 chunk search | 1 query | 1 query |
| Title similarity search | -- | 1 query (NEW) |
| Document metadata fetch | up to 10 queries (N+1) | 1 query (batch) |
| **Total DB round-trips** | **3-13** | **4** |

Net improvement despite adding a new feature.

## Configuration & Tuning

| Parameter | Default | Location | Purpose |
|-----------|---------|----------|---------|
| `TITLE_BOOST_WEIGHT` | `1.5` | `config.py` | RRF weight multiplier for title signal |
| `SEARCH_TOP_K` | `50` | `config.py` | Candidates per retrieval path (existing) |
| `RERANK_TOP_N` | `10` | `config.py` | Final results after reranking (existing) |
| `RRF_K` | `60` | `config.py` | RRF smoothing constant (existing) |

**Tuning guidance for `TITLE_BOOST_WEIGHT`:**
- `1.0` = title treated equally to content signals (mild tiebreaker)
- `1.5` = title gets 50% more influence (recommended starting point)
- `2.0` = title counts double (strong preference for title matches)
- `>2.5` = title dominates; content matches rarely outrank title matches

## Testing Strategy

No test framework exists yet. Manual testing approach:

1. **Title boost verification:** Search "remote work policy" -- document titled "Remote Work Policy" should rank #1 or #2
2. **Content-beats-title test:** Search a specific phrase known to appear deep in a document with a non-matching title -- that document should still surface
3. **Version filter ON:** Search for a policy that has v1 and v2 -- only v2 should appear
4. **Version filter OFF:** Same search -- both versions appear, v2 ranked higher
5. **Mixed scenario:** Search a term that matches one doc's title AND another doc's content -- both should appear, with tunable relative ranking

## Files Modified

| File | Change |
|------|--------|
| `backend/db/init.sql` | Add versioning columns, title embeddings table |
| `backend/app/models/db.py` | Add ORM fields + new model |
| `backend/app/models/schemas.py` | Add version/group to response, show_latest_only to request |
| `backend/app/core/config.py` | Add TITLE_BOOST_WEIGHT |
| `backend/app/services/ingestion.py` | Version detection, title embedding, BM25 fix |
| `backend/app/services/search.py` | Third signal, weighted RRF, batch fetch, parameterized SQL, version filter, filters support |
| `backend/app/api/search.py` | Pass show_latest_only through |
| `frontend/app/search/page.tsx` | Version toggle, version badge |
| `frontend/lib/api.ts` | Add show_latest_only param |
