import httpx

from app.core.config import settings


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the embedding service (Colab or local) to generate vectors."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.EMBEDDING_API_URL,
            json={"texts": texts},
        )
        response.raise_for_status()
        return response.json()["embeddings"]


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding."""
    results = await generate_embeddings([text])
    return results[0]
