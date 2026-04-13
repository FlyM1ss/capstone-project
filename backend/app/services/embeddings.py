import httpx

from app.core.config import settings


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the embedding service to generate vectors, batching to avoid timeouts."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), settings.EMBED_BATCH_SIZE):
            batch = texts[i : i + settings.EMBED_BATCH_SIZE]
            response = await client.post(
                settings.EMBEDDING_API_URL,
                json={"texts": batch},
            )
            response.raise_for_status()
            all_embeddings.extend(response.json()["embeddings"])
        return all_embeddings


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding."""
    results = await generate_embeddings([text])
    return results[0]
