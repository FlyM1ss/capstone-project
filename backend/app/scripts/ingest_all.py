"""Batch ingest documents from /data/ directories (fully synchronous).

Usage:
  python -m app.scripts.ingest_all              # Ingest clean data only (sample-docs + auxiliary)
  python -m app.scripts.ingest_all --poisoned    # Ingest poisoned data only (for adversarial testing)
  python -m app.scripts.ingest_all --all         # Ingest everything (clean + poisoned)
"""
import argparse
import os
import uuid
from pathlib import Path

import httpx
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PowerpointFormatOption
from docling.pipeline.simple_pipeline import SimplePipeline
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.ingestion import _extract_version_info, chunk_text

# Sync engine (swap asyncpg -> psycopg2)
sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
engine = create_engine(sync_url, echo=False)

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")


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

    # Use cleaned filename as title (more reliable than parsed text for diverse PDFs)
    if not title:
        title = Path(file_path).stem.replace("_", " ").replace("-", " ").strip()

    # 2. Extract version info
    document_group, version = _extract_version_info(file_path)

    # 3. Insert document
    doc_id = str(uuid.uuid4())
    db.execute(text("""
        INSERT INTO documents (id, title, doc_type, category, access_level, file_path, page_count, document_group, version)
        VALUES (:id, :title, :doc_type, :category, :access_level, :file_path, :page_count, :document_group, :version)
    """), {
        "id": doc_id,
        "title": title,
        "doc_type": Path(file_path).suffix.lstrip("."),
        "category": category,
        "access_level": access_level,
        "file_path": file_path,
        "page_count": page_count,
        "document_group": document_group,
        "version": version,
    })

    # 4. Chunk text
    chunks = chunk_text(full_text)

    # 5. Generate embeddings (title + chunks in one batch)
    texts_to_embed = [title] + chunks if chunks else [title]
    all_embeddings = generate_embeddings_sync(texts_to_embed)
    title_embedding = all_embeddings[0]
    chunk_embeddings = all_embeddings[1:] if chunks else []

    # 6. Store title embedding
    db.execute(text("""
        INSERT INTO document_title_embeddings (id, document_id, title_text, embedding)
        VALUES (:id, :doc_id, :title_text, :embedding)
    """), {
        "id": str(uuid.uuid4()),
        "doc_id": doc_id,
        "title_text": title,
        "embedding": str(title_embedding),
    })

    # 7. Store chunks
    for i, (chunk_content, embedding) in enumerate(zip(chunks, chunk_embeddings)):
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
    result = db.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_chunks_bm25'"
    ))
    if result.fetchone() is None:
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


CLEAN_DIRS = ["/data/sample-docs", "/data/auxiliary"]
POISONED_DIRS = ["/data/poisoned"]


def collect_files(dirs: list[str]) -> list[str]:
    """Collect all supported document files from the given directories."""
    files = []
    for docs_dir in dirs:
        if not os.path.isdir(docs_dir):
            print(f"Skipping {docs_dir} (not found)")
            continue
        for filename in os.listdir(docs_dir):
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                files.append(os.path.join(docs_dir, filename))
    return sorted(files)


def ingest_files(files: list[str]):
    """Ingest a list of document files."""
    print(f"Found {len(files)} documents to ingest")

    for i, path in enumerate(files):
        filename = os.path.basename(path)
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


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the search engine")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--poisoned", action="store_true",
                       help="Ingest only poisoned/adversarial data")
    group.add_argument("--all", action="store_true",
                       help="Ingest both clean and poisoned data")
    args = parser.parse_args()

    if args.poisoned:
        print("=== Ingesting POISONED data only ===")
        files = collect_files(POISONED_DIRS)
    elif args.all:
        print("=== Ingesting ALL data (clean + poisoned) ===")
        files = collect_files(CLEAN_DIRS + POISONED_DIRS)
    else:
        print("=== Ingesting CLEAN data only ===")
        files = collect_files(CLEAN_DIRS)

    ingest_files(files)


if __name__ == "__main__":
    main()
