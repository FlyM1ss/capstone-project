import asyncio
import uuid
from pathlib import Path

from docling.document_converter import DocumentConverter
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Document, DocumentChunk
from app.services.embeddings import generate_embeddings


def _parse_document(file_path: str) -> tuple[str, int | None]:
    """Synchronous Docling parsing — runs in a thread pool."""
    converter = DocumentConverter()
    result = converter.convert(file_path)
    full_text = result.document.export_to_markdown()
    page_count = result.document.num_pages() if hasattr(result.document, "num_pages") else None
    return full_text, page_count


def chunk_text(text_content: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text_content.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start = end - overlap
    return chunks


async def ingest_document(
    db: AsyncSession,
    file_path: str,
    title: str | None = None,
    author: str | None = None,
    category: str = "report",
    access_level: str = "public",
) -> tuple[Document, int]:
    """Parse a PDF, chunk it, embed chunks, and store everything."""
    # 1. Parse with Docling (run in thread to avoid blocking async event loop)
    full_text, page_count = await asyncio.to_thread(_parse_document, file_path)

    # Infer title (skip image tags, empty lines, and HTML comments)
    if not title:
        for line in full_text.strip().split("\n"):
            line = line.strip().strip("#").strip()
            if line and not line.startswith("<!--") and not line.startswith("!["):
                title = line[:200]
                break
        if not title:
            title = Path(file_path).stem

    # 2. Create document record
    doc = Document(
        title=title,
        author=author,
        doc_type=Path(file_path).suffix.lstrip("."),
        category=category,
        access_level=access_level,
        file_path=file_path,
        page_count=page_count,
    )
    db.add(doc)
    await db.flush()  # Get doc.id

    # 3. Chunk text
    chunks = chunk_text(full_text)
    if not chunks:
        await db.commit()
        return doc, 0

    # 4. Generate embeddings (batch)
    embeddings = await generate_embeddings(chunks)

    # 5. Store chunks with embeddings
    for i, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk_text_content,
            embedding=embedding,
        )
        db.add(chunk)

    await db.commit()

    # 6. Ensure ParadeDB BM25 index exists
    await _ensure_bm25_index(db)

    return doc, len(chunks)


async def _ensure_bm25_index(db: AsyncSession):
    """Create ParadeDB BM25 index if it doesn't exist."""
    try:
        await db.execute(text("""
            CALL paradedb.create_bm25(
                index_name => 'idx_chunks_bm25',
                table_name => 'document_chunks',
                key_field => 'id',
                text_fields => paradedb.field('content')
            )
        """))
        await db.commit()
    except Exception:
        # Index may already exist
        await db.rollback()
