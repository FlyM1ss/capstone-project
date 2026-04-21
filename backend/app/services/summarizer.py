import logging

import cohere

from app.core.config import settings
from app.models.db import Document, DocumentChunk

logger = logging.getLogger(__name__)

MODEL = "command-r-08-2024"
MAX_INPUT_CHARS = 8000
TEMPERATURE = 0.3


class SummarizerUnavailable(Exception):
    """Raised when the summarizer cannot produce a summary.

    Caught by a FastAPI exception handler in app.main and translated to 503.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(f"Summarizer unavailable: {reason}")
        self.reason = reason


def _build_prompt(title: str, author: str | None, content: str) -> str:
    author_line = f"Author: {author}\n" if author else ""
    return (
        "You are summarizing an internal business document for employees "
        "searching a company knowledge base.\n\n"
        f"Document title: {title}\n"
        f"{author_line}"
        "\n"
        "Document content:\n"
        f"{content}\n\n"
        "Produce 5-7 concise bullet points capturing the most useful takeaways: "
        "key facts, decisions, figures, and conclusions. Each bullet starts with "
        '"- " on its own line. No preamble, no closing remark, no headers.'
    )


def _normalize_bullets(raw: str) -> str:
    """Strip preambles and normalize bullet markers to '- '."""
    lines = [line.rstrip() for line in raw.strip().splitlines()]
    bullets: list[str] = []
    for line in lines:
        stripped = line.lstrip()
        if not stripped:
            continue
        # Accept -, •, *, or numeric prefix; normalize to "- "
        if stripped.startswith(("- ", "* ", "• ")):
            bullets.append("- " + stripped[2:].strip())
        elif stripped[:2].rstrip(".").isdigit() and ". " in stripped[:4]:
            bullets.append("- " + stripped.split(". ", 1)[1].strip())
        elif bullets:
            # Continuation of previous bullet — append with space.
            bullets[-1] += " " + stripped
    return "\n".join(bullets)


async def generate_summary(document: Document, chunks: list[DocumentChunk]) -> str:
    """Generate a bulleted summary for a document using Cohere Chat."""
    if not settings.COHERE_API_KEY:
        raise SummarizerUnavailable("COHERE_API_KEY is not configured")

    content_parts: list[str] = []
    remaining = MAX_INPUT_CHARS
    for chunk in chunks:
        if remaining <= 0:
            break
        piece = chunk.content[:remaining]
        content_parts.append(piece)
        remaining -= len(piece)

    content = "\n\n".join(content_parts).strip()
    if not content:
        raise SummarizerUnavailable("document has no text content to summarize")

    prompt = _build_prompt(document.title, document.author, content)

    try:
        co = cohere.AsyncClient(settings.COHERE_API_KEY)
        response = await co.chat(
            model=MODEL,
            message=prompt,
            temperature=TEMPERATURE,
        )
    except Exception as exc:
        logger.warning("Cohere summarization failed: %s", exc)
        raise SummarizerUnavailable(f"cohere call failed: {exc}") from exc

    text = getattr(response, "text", "") or ""
    bullets = _normalize_bullets(text)
    if not bullets:
        raise SummarizerUnavailable("empty response from model")
    return bullets
