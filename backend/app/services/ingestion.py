import asyncio
import re
import uuid
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PowerpointFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Document, DocumentChunk, DocumentTitleEmbedding
from app.services.embeddings import generate_embedding, generate_embeddings


def _parse_document(file_path: str) -> tuple[str, int | None]:
    """Synchronous Docling parsing — runs in a thread pool."""
    converter = DocumentConverter(
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.DOCX,
            InputFormat.PPTX,
        ],
        format_options={
            InputFormat.PPTX: PowerpointFormatOption(
                pipeline_cls=SimplePipeline,
            ),
        },
    )
    result = converter.convert(Path(file_path))
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


async def ingest_document(
    db: AsyncSession,
    file_path: str,
    title: str | None = None,
    author: str | None = None,
    category: str = "report",
    access_level: str = "public",
) -> tuple[Document, int]:
    """Parse a document, chunk it, embed chunks and title, and store everything."""
    # 1. Parse with Docling (run in thread to avoid blocking async event loop)
    full_text, page_count = await asyncio.to_thread(_parse_document, file_path)

    # Use cleaned filename as title (more reliable than parsed text for diverse PDFs)
    if not title:
        title = Path(file_path).stem.replace("_", " ").replace("-", " ").strip()

    # 2. Extract version info from filename
    document_group, version = _extract_version_info(file_path)

    # 3. Create document record
    doc = Document(
        title=title,
        author=author,
        doc_type=Path(file_path).suffix.lstrip("."),
        category=category,
        access_level=access_level,
        file_path=file_path,
        page_count=page_count,
        document_group=document_group,
        version=version,
    )
    db.add(doc)
    await db.flush()  # Get doc.id

    # 4. Chunk text
    chunks = chunk_text(full_text)

    # 5. Generate title embedding and chunk embeddings
    # Batch title + all chunks together to minimize API calls
    texts_to_embed = [title] + chunks if chunks else [title]
    all_embeddings = await generate_embeddings(texts_to_embed)
    title_embedding = all_embeddings[0]
    chunk_embeddings = all_embeddings[1:] if chunks else []

    # 6. Store title embedding
    title_emb = DocumentTitleEmbedding(
        document_id=doc.id,
        title_text=title,
        embedding=title_embedding,
    )
    db.add(title_emb)

    # 7. Store chunks with embeddings
    for i, (chunk_text_content, embedding) in enumerate(zip(chunks, chunk_embeddings)):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk_text_content,
            embedding=embedding,
        )
        db.add(chunk)

    await db.commit()

    # 8. Ensure ParadeDB BM25 index exists
    if chunks:
        await _ensure_bm25_index(db)

    return doc, len(chunks)


async def _ensure_bm25_index(db: AsyncSession):
    """Create ParadeDB BM25 index if it doesn't exist."""
    result = await db.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_chunks_bm25'"
    ))
    if result.fetchone() is None:
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
            await db.rollback()
