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
) -> tuple[list[SearchResultItem], int]:
    """Execute hybrid search: semantic + BM25, RRF merge, rerank."""
    start = time.time()

    # 1. Generate query embedding
    query_embedding = await generate_embedding(query)

    # 2. Build access level filter
    access_levels = _get_access_levels(user_role)
    access_filter = ", ".join(f"'{a}'" for a in access_levels)

    # 3. Semantic search (pgvector cosine similarity)
    semantic_sql = text(f"""
        SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
               1 - (dc.embedding <=> CAST(:embedding AS vector)) AS score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.access_level IN ({access_filter})
        ORDER BY dc.embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """)
    semantic_result = await db.execute(
        semantic_sql,
        {"embedding": str(query_embedding), "top_k": settings.SEARCH_TOP_K},
    )
    semantic_rows = semantic_result.fetchall()

    # 4. BM25 keyword search (ParadeDB)
    bm25_rows = []
    try:
        bm25_sql = text(f"""
            SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
                   paradedb.score(dc.id) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.id @@@ paradedb.parse(:query)
              AND d.access_level IN ({access_filter})
            ORDER BY paradedb.score(dc.id) DESC
            LIMIT :top_k
        """)
        bm25_result = await db.execute(
            bm25_sql, {"query": query, "top_k": settings.SEARCH_TOP_K},
        )
        bm25_rows = bm25_result.fetchall()
    except Exception:
        # BM25 index may not exist yet — rollback to clear failed transaction state
        await db.rollback()

    # 5. Reciprocal Rank Fusion
    merged = _rrf_merge(semantic_rows, bm25_rows, k=settings.RRF_K)

    if not merged:
        latency_ms = int((time.time() - start) * 1000)
        return [], latency_ms

    # 6. Rerank with Cohere
    top_chunks = merged[:settings.SEARCH_TOP_K]
    chunk_texts = [c["content"] for c in top_chunks]
    chunk_ids = [c["id"] for c in top_chunks]

    reranked_indices = await rerank_results(query, chunk_texts, top_n=top_k)

    # 7. Build final results (group by document)
    seen_docs = set()
    results = []
    for idx in reranked_indices:
        chunk = top_chunks[idx]
        doc_id = chunk["document_id"]
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        # Fetch document metadata
        doc_sql = text("SELECT * FROM documents WHERE id = :doc_id")
        doc_row = (await db.execute(doc_sql, {"doc_id": doc_id})).fetchone()
        if doc_row:
            results.append(SearchResultItem(
                document_id=doc_row.id,
                title=doc_row.title,
                author=doc_row.author,
                doc_type=doc_row.doc_type,
                category=doc_row.category,
                access_level=doc_row.access_level,
                snippet=chunk["content"][:300],
                score=chunk["rrf_score"],
                page_count=doc_row.page_count,
                created_date=doc_row.created_date,
            ))

    latency_ms = int((time.time() - start) * 1000)
    return results, latency_ms


def _get_access_levels(role: str) -> list[str]:
    if role == "admin":
        return ["public", "internal", "confidential"]
    elif role == "manager":
        return ["public", "internal"]
    return ["public"]


def _rrf_merge(semantic_rows, bm25_rows, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion: combine two ranked lists."""
    scores: dict[str, dict] = {}

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

    merged = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return merged
