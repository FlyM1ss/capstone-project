import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingServiceUnavailable(Exception):
    """Raised when the embedding service is unreachable or returns an invalid response.

    Caught by a FastAPI exception handler in app.main and translated to 503.
    """

    def __init__(self, reason: str, url: str) -> None:
        super().__init__(f"Embedding service at {url} unavailable: {reason}")
        self.reason = reason
        self.url = url


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the embedding service to generate vectors, batching to avoid timeouts."""
    url = settings.EMBEDDING_API_URL
    async with httpx.AsyncClient(timeout=300.0) as client:
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), settings.EMBED_BATCH_SIZE):
            batch = texts[i : i + settings.EMBED_BATCH_SIZE]
            try:
                response = await client.post(url, json={"texts": batch})
                response.raise_for_status()
                all_embeddings.extend(response.json()["embeddings"])
            except httpx.ConnectError as exc:
                logger.warning("Embedding service unreachable at %s: %s", url, exc)
                raise EmbeddingServiceUnavailable("connection failed", url) from exc
            except httpx.TimeoutException as exc:
                logger.warning("Embedding service timed out at %s: %s", url, exc)
                raise EmbeddingServiceUnavailable("timeout", url) from exc
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Embedding service at %s returned HTTP %s",
                    url, exc.response.status_code,
                )
                raise EmbeddingServiceUnavailable(
                    f"upstream status {exc.response.status_code}", url,
                ) from exc
            except (KeyError, ValueError) as exc:
                logger.warning("Embedding service at %s returned malformed response: %s", url, exc)
                raise EmbeddingServiceUnavailable("malformed response", url) from exc
        return all_embeddings


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding."""
    results = await generate_embeddings([text])
    return results[0]
