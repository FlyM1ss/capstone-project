"""Batch ingest documents from /data/ directories.

Usage:
  python -m app.scripts.ingest_all              # Ingest clean data only (sample-docs + auxiliary)
  python -m app.scripts.ingest_all --poisoned    # Ingest poisoned data only (for adversarial testing)
  python -m app.scripts.ingest_all --all         # Ingest everything (clean + poisoned)
  python -m app.scripts.ingest_all --clean        # Wipe all data, then ingest clean data
"""
import argparse
import asyncio
import os

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import async_session
from app.services.ingestion import ingest_document

# Sync engine only used for clean_all_data (simple destructive op)
_sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, echo=False)

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")
CLEAN_DIRS = ["/data/sample-docs", "/data/auxiliary"]
POISONED_DIRS = ["/data/poisoned"]


def clean_all_data():
    """Wipe all document data and the BM25 index for a fresh start."""
    with Session(_sync_engine) as db:
        db.execute(text("DROP INDEX IF EXISTS idx_chunks_bm25"))
        db.execute(text("TRUNCATE documents CASCADE"))
        db.commit()
    print("All document data cleared.")


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


async def _ingest_one(path: str) -> tuple[str, int] | None:
    """Ingest a single file using the shared async service."""
    async with async_session() as db:
        result = await ingest_document(db, path)
        if result is None:
            return None
        doc, chunk_count = result
        return doc.title, chunk_count


async def _ingest_files(files: list[str]):
    """Ingest a list of document files."""
    print(f"Found {len(files)} documents to process")
    ingested = 0
    skipped = 0

    for i, path in enumerate(files):
        filename = os.path.basename(path)
        print(f"[{i+1}/{len(files)}] {filename}...", end=" ", flush=True)
        try:
            result = await _ingest_one(path)
            if result is None:
                print("SKIPPED (unchanged)")
                skipped += 1
            else:
                title, chunks = result
                print(f"OK ({chunks} chunks)")
                ingested += 1
        except Exception as e:
            print(f"ERROR: {e}")

    print(f"\nDone! Ingested: {ingested}, Skipped: {skipped}, Total: {len(files)}")


def main():
    parser = argparse.ArgumentParser(description="Ingest documents into the search engine")
    parser.add_argument("--clean", action="store_true",
                        help="Wipe all document data before ingesting")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--poisoned", action="store_true",
                       help="Ingest only poisoned/adversarial data")
    group.add_argument("--all", action="store_true",
                       help="Ingest both clean and poisoned data")
    args = parser.parse_args()

    if args.clean:
        print("=== Cleaning all document data ===")
        clean_all_data()

    if args.poisoned:
        print("=== Ingesting POISONED data only ===")
        files = collect_files(POISONED_DIRS)
    elif args.all:
        print("=== Ingesting ALL data (clean + poisoned) ===")
        files = collect_files(CLEAN_DIRS + POISONED_DIRS)
    else:
        print("=== Ingesting CLEAN data only ===")
        files = collect_files(CLEAN_DIRS)

    asyncio.run(_ingest_files(files))


if __name__ == "__main__":
    main()
