import re
import time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.schemas import SearchResultItem
from app.services.embeddings import generate_embedding
from app.services.reranker import rerank_results


async def hybrid_search(
    db: AsyncSession,
    query: str,
    filters: dict | None = None,
    user_role: str = "analyst",
    top_k: int = 10,
    show_latest_only: bool = True,
) -> tuple[list[SearchResultItem], int]:
    """Execute hybrid search: semantic + BM25 + title similarity, RRF merge, rerank."""
    start = time.time()

    # 1. Generate query embedding
    query_embedding = await generate_embedding(query)

    # 2. Build access level filter (parameterized — no f-string injection)
    access_levels = _get_access_levels(user_role)
    access_params = {f"access_{i}": level for i, level in enumerate(access_levels)}
    access_placeholders = ", ".join(f":access_{i}" for i in range(len(access_levels)))

    # 3. Build optional filters
    category_clause = ""
    category_params = {}
    if filters and filters.get("category"):
        category_clause = "AND d.category = :filter_category"
        category_params["filter_category"] = filters["category"]

    doc_type_clause = ""
    doc_type_params = {}
    if filters and filters.get("doc_type"):
        doc_type_clause = "AND d.doc_type = :filter_doc_type"
        doc_type_params["filter_doc_type"] = filters["doc_type"]

    # Combine all filter params for reuse across queries
    filter_params = {**access_params, **category_params, **doc_type_params}

    # 4. Semantic search (pgvector cosine similarity)
    semantic_sql = text(f"""
        SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
               1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.access_level IN ({access_placeholders})
        {category_clause}
        {doc_type_clause}
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)
    semantic_result = await db.execute(
        semantic_sql,
        {"embedding": str(query_embedding), "top_k": settings.SEARCH_TOP_K,
         **filter_params},
    )
    semantic_rows = semantic_result.fetchall()

    # 5. BM25 keyword search (ParadeDB)
    bm25_rows = []
    bm25_query = _sanitize_bm25_query(query)
    if bm25_query:
        try:
            bm25_sql = text(f"""
                SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
                       paradedb.score(dc.id) AS score
                FROM document_chunks dc
                JOIN documents d ON dc.document_id = d.id
                WHERE dc.id @@@ paradedb.parse(:query)
                  AND d.access_level IN ({access_placeholders})
                  {category_clause}
                  {doc_type_clause}
                ORDER BY paradedb.score(dc.id) DESC
                LIMIT :top_k
            """)
            bm25_result = await db.execute(
                bm25_sql, {"query": bm25_query, "top_k": settings.SEARCH_TOP_K,
                           **filter_params},
            )
            bm25_rows = bm25_result.fetchall()
        except Exception:
            await db.rollback()

    # 6. Title similarity search (pgvector on title embeddings)
    title_sql = text(f"""
        SELECT dte.document_id,
               1 - (dte.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_title_embeddings dte
        JOIN documents d ON dte.document_id = d.id
        WHERE d.access_level IN ({access_placeholders})
        {category_clause}
        {doc_type_clause}
        ORDER BY dte.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)
    title_rows = []
    try:
        title_result = await db.execute(
            title_sql,
            {"embedding": str(query_embedding), "top_k": settings.SEARCH_TOP_K,
             **filter_params},
        )
        title_rows = title_result.fetchall()
    except Exception:
        await db.rollback()

    # 7. Reciprocal Rank Fusion (3 lists, title weighted)
    merged = _rrf_merge(
        semantic_rows, bm25_rows, title_rows,
        k=settings.RRF_K,
        title_weight=settings.TITLE_BOOST_WEIGHT,
    )

    if not merged:
        latency_ms = int((time.time() - start) * 1000)
        return [], latency_ms

    # 8. Rerank with Cohere
    top_chunks = merged[:settings.SEARCH_TOP_K]
    chunk_texts = [c["content"] for c in top_chunks]

    reranked_indices = await rerank_results(query, chunk_texts, top_n=top_k)

    # 9. Batch fetch document metadata (fix N+1 query)
    doc_ids = list({c["document_id"] for c in top_chunks})
    doc_id_params = {f"did_{i}": did for i, did in enumerate(doc_ids)}
    doc_id_placeholders = ", ".join(f":did_{i}" for i in range(len(doc_ids)))
    doc_sql = text(f"SELECT * FROM documents WHERE id IN ({doc_id_placeholders})")
    doc_rows = (await db.execute(doc_sql, doc_id_params)).fetchall()
    doc_map = {row.id: row for row in doc_rows}

    # 10. Build final results (group by document)
    seen_docs = set()
    results = []
    for idx in reranked_indices:
        chunk = top_chunks[idx]
        doc_id = chunk["document_id"]
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        doc_row = doc_map.get(doc_id)
        if doc_row:
            snippet = chunk["content"][:300] if chunk["content"] else doc_row.title
            results.append(SearchResultItem(
                document_id=doc_row.id,
                title=doc_row.title,
                author=doc_row.author,
                doc_type=doc_row.doc_type,
                category=doc_row.category,
                access_level=doc_row.access_level,
                snippet=snippet,
                score=chunk["rrf_score"],
                page_count=doc_row.page_count,
                created_date=doc_row.created_date,
                version=doc_row.version,
                document_group=doc_row.document_group,
            ))

    # 11. Version filtering
    if show_latest_only:
        results = _filter_latest_versions(results)

    latency_ms = int((time.time() - start) * 1000)
    return results, latency_ms


def _sanitize_bm25_query(query: str) -> str:
    """Strip characters that break Tantivy's query parser (used by ParadeDB BM25)."""
    # Remove Tantivy special chars: + - && || ! ( ) { } [ ] ^ " ~ * ? : \ / '
    sanitized = re.sub(r"[+\-&|!(){}\[\]^\"~*?:\\/']", " ", query)
    # Collapse whitespace and strip
    return " ".join(sanitized.split())


def _get_access_levels(role: str) -> list[str]:
    if role == "admin":
        return ["public", "internal", "confidential"]
    elif role == "manager":
        return ["public", "internal"]
    return ["public"]


def _filter_latest_versions(results: list[SearchResultItem]) -> list[SearchResultItem]:
    """Keep only the latest version per document_group."""
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


def _rrf_merge(
    semantic_rows,
    bm25_rows,
    title_rows,
    k: int = 60,
    title_weight: float = 1.5,
) -> list[dict]:
    """Reciprocal Rank Fusion: combine three ranked lists (semantic, BM25, title)."""
    scores: dict[str, dict] = {}

    # Semantic chunk scores
    for rank, row in enumerate(semantic_rows):
        chunk_id = str(row.id)
        if chunk_id not in scores:
            scores[chunk_id] = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "rrf_score": 0.0,
            }
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # BM25 chunk scores
    for rank, row in enumerate(bm25_rows):
        chunk_id = str(row.id)
        if chunk_id not in scores:
            scores[chunk_id] = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "rrf_score": 0.0,
            }
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    # Title scores: boost all chunks belonging to title-matched documents
    title_doc_scores: dict[str, float] = {}
    title_doc_ids_with_chunks: set[str] = set()
    for rank, row in enumerate(title_rows):
        doc_id = str(row.document_id)
        if doc_id not in title_doc_scores:
            title_doc_scores[doc_id] = title_weight * (1.0 / (k + rank + 1))

    # Boost existing chunks from title-matched documents
    for chunk_id, chunk_data in scores.items():
        doc_id = str(chunk_data["document_id"])
        if doc_id in title_doc_scores:
            chunk_data["rrf_score"] += title_doc_scores[doc_id]
            title_doc_ids_with_chunks.add(doc_id)

    # Add title-only matches (documents with no chunk hits) as synthetic entries
    for doc_id, title_score in title_doc_scores.items():
        if doc_id not in title_doc_ids_with_chunks:
            # Find the matching title row to get document_id as UUID
            for row in title_rows:
                if str(row.document_id) == doc_id:
                    synthetic_id = f"title_{doc_id}"
                    scores[synthetic_id] = {
                        "id": row.document_id,  # use doc_id as chunk id placeholder
                        "document_id": row.document_id,
                        "content": "",  # snippet will be populated from doc metadata
                        "chunk_index": -1,
                        "rrf_score": title_score,
                    }
                    break

    merged = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return merged
