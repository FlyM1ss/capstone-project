import cohere

from app.core.config import settings


async def rerank_results(query: str, texts: list[str], top_n: int = 10) -> list[int]:
    """Rerank texts using Cohere Rerank and return indices of top results."""
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
        # Fallback: return original order
        return list(range(min(top_n, len(texts))))
