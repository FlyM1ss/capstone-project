"""Batch ingest all PDFs in /data/sample-docs/ (fully synchronous)."""
import os
import uuid
from pathlib import Path

import httpx
from docling.document_converter import DocumentConverter
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings

# Sync engine (swap asyncpg → psycopg2)
sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_url, echo=False)


def chunk_text(text_content: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
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


def generate_embeddings_sync(texts: list[str]) -> list[list[float]]:
    with httpx.Client(timeout=120.0) as client:
        response = client.post(
            settings.EMBEDDING_API_URL,
            json={"texts": texts},
        )
        response.raise_for_status()
        return response.json()["embeddings"]


def ingest_document(
    db: Session,
    file_path: str,
    title: str | None = None,
    category: str = "report",
    access_level: str = "public",
) -> tuple[str, int]:
    # 1. Parse with Docling
    converter = DocumentConverter()
    result = converter.convert(file_path)
    full_text = result.document.export_to_markdown()
    page_count = result.document.num_pages() if hasattr(result.document, "num_pages") else None

    # Use cleaned filename as title (more reliable than parsed text for diverse PDFs)
    if not title:
        title = Path(file_path).stem.replace("_", " ").replace("-", " ").strip()

    # 2. Insert document
    doc_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO documents (id, title, doc_type, category, access_level, file_path, page_count)
        VALUES (:id, :title, :doc_type, :category, :access_level, :file_path, :page_count)
    """), {
        "id": doc_id,
        "title": title,
        "doc_type": Path(file_path).suffix.lstrip("."),
        "category": category,
        "access_level": access_level,
        "file_path": file_path,
        "page_count": page_count,
    })

    # 3. Chunk text
    chunks = chunk_text(full_text)
    if not chunks:
        db.commit()
        return title, 0

    # 4. Generate embeddings
    embeddings = generate_embeddings_sync(chunks)

    # 5. Store chunks
    for i, (chunk_content, embedding) in enumerate(zip(chunks, embeddings)):
        db.execute(text("""
            INSERT INTO document_chunks (id, document_id, chunk_index, content, embedding)
            VALUES (:id, :doc_id, :idx, :content, :embedding)
        """), {
            "id": str(uuid.uuid4()),
            "doc_id": doc_id,
            "idx": i,
            "content": chunk_content,
            "embedding": str(embedding),
        })

    db.commit()
    return title, len(chunks)


def ensure_bm25_index(db: Session):
    try:
        db.execute(text("""
            CALL paradedb.create_bm25(
                index_name => 'idx_chunks_bm25',
                table_name => 'document_chunks',
                key_field => 'id',
                text_fields => paradedb.field('content')
            )
        """))
        db.commit()
    except Exception:
        db.rollback()


def main():
    docs_dir = "/data/sample-docs"
    files = [f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx", ".pptx"))]
    print(f"Found {len(files)} documents to ingest")

    for i, filename in enumerate(files):
        path = os.path.join(docs_dir, filename)
        print(f"[{i+1}/{len(files)}] Ingesting {filename}...")
        try:
            with Session(engine) as db:
                title, chunks = ingest_document(db, path)
                print(f"  -> {title}: {chunks} chunks")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    # Create BM25 index after all docs are ingested
    with Session(engine) as db:
        ensure_bm25_index(db)

    print("Done!")


if __name__ == "__main__":
    main()
