from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.schemas import SearchRequest, SearchResponse
from app.services.search import hybrid_search
from app.services.validation import validate_query

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db_session),
):
    # Validate input
    validate_query(body.query)

    # TODO: extract user role from auth token; default to analyst for now
    user_role = "admin"  # permissive for demo

    results, latency_ms = await hybrid_search(
        db, body.query, filters=body.filters,
        user_role=user_role, top_k=body.top_k,
        show_latest_only=body.show_latest_only,
        show_oldest_only=body.show_oldest_only,
    )

    return SearchResponse(
        query=body.query,
        results=results,
        total=len(results),
        latency_ms=latency_ms,
    )
