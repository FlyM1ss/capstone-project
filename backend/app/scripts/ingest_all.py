"""Batch ingest documents from /data/ directories.

Usage:
  python -m app.scripts.ingest_all
      # Default clean ingest (generic + auxiliary)

  python -m app.scripts.ingest_all --poisoned
      # Adversarial ingest (malformed + prompt-injected + legacy poisoned)

  python -m app.scripts.ingest_all --all
      # Everything (clean + adversarial)

  python -m app.scripts.ingest_all --clean
      # Wipe DB first, then ingest using selected mode/categories

  python -m app.scripts.ingest_all --mode prompt-injected
      # Only prompt-injected documents

  python -m app.scripts.ingest_all --categories generic malformed
      # Explicit category subset from /data root

  python -m app.scripts.ingest_all --dirs /data/generic /data/malformed
      # Explicit directories (bypasses category/mode resolution)
"""
import argparse
import asyncio
import os
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import async_session
from app.services.ingestion import ingest_document

# Sync engine only used for clean_all_data (simple destructive op)
_sync_url = settings.DATABASE_URL.replace("+asyncpg", "")
_sync_engine = create_engine(_sync_url, echo=False)

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")
DEFAULT_DATA_ROOT = os.getenv("INGEST_DATA_ROOT", "/data")

MODE_TO_CATEGORIES = {
    "clean": ["generic", "auxiliary"],
    "poisoned": ["malformed", "prompt-injected", "poisoned"],
    "all": ["generic", "auxiliary", "malformed", "prompt-injected", "poisoned"],
    "generic": ["generic"],
    "auxiliary": ["auxiliary"],
    "malformed": ["malformed"],
    "prompt-injected": ["prompt-injected"],
}

CATEGORY_CHOICES = [
    "generic",
    "auxiliary",
    "malformed",
    "prompt-injected",
    "poisoned",
    "sample-docs",
    "sample",
]


def clean_all_data():
    """Wipe all document data and the BM25 index for a fresh start."""
    with Session(_sync_engine) as db:
        db.execute(text("DROP INDEX IF EXISTS idx_chunks_bm25"))
        db.execute(text("TRUNCATE documents CASCADE"))
        db.commit()
    print("All document data cleared.")


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen = set()
    ordered = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        ordered.append(item)
    return ordered


def _resolve_mode(args: argparse.Namespace) -> str:
    if args.poisoned:
        return "poisoned"
    if args.all:
        return "all"
    return args.mode


def _resolve_categories(args: argparse.Namespace) -> list[str]:
    if args.categories:
        categories = list(args.categories)
    else:
        mode = _resolve_mode(args)
        categories = MODE_TO_CATEGORIES[mode]

    # Compatibility fallback for older datasets: if generic is missing, try sample-docs.
    data_root = Path(args.data_root)
    if "generic" in categories:
        generic_dir = data_root / "generic"
        legacy_dir = data_root / "sample-docs"
        if not generic_dir.is_dir() and legacy_dir.is_dir() and "sample-docs" not in categories:
            print("'generic' not found; falling back to legacy 'sample-docs'.")
            categories = list(categories) + ["sample-docs"]

    return _dedupe_preserve_order(list(categories))


def _resolve_target_dirs(args: argparse.Namespace) -> tuple[list[str], list[str] | None, str | None]:
    if args.dirs:
        return list(args.dirs), None, None

    categories = _resolve_categories(args)
    data_root = Path(args.data_root)
    dirs = [str(data_root / category) for category in categories]
    return dirs, categories, _resolve_mode(args)


def collect_files(dirs: list[str], recursive: bool = False, fail_on_missing: bool = False) -> list[str]:
    """Collect all supported document files from the given directories."""
    files: set[str] = set()
    missing: list[str] = []

    for docs_dir in dirs:
        docs_path = Path(docs_dir)
        if not docs_path.is_dir():
            print(f"Skipping {docs_dir} (not found)")
            missing.append(docs_dir)
            continue

        if recursive:
            candidates = docs_path.rglob("*")
        else:
            candidates = docs_path.iterdir()

        for file_path in candidates:
            if file_path.is_file() and file_path.suffix.lower() in SUPPORTED_EXTENSIONS:
                files.add(str(file_path))

    if fail_on_missing and missing:
        raise FileNotFoundError(f"Required ingest directories were not found: {', '.join(missing)}")

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
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Wipe all document data before ingesting",
    )

    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--mode",
        choices=list(MODE_TO_CATEGORIES.keys()),
        default="clean",
        help="Ingest mode (default: clean)",
    )
    mode_group.add_argument(
        "--poisoned",
        action="store_true",
        help="Backward-compatible shortcut for '--mode poisoned'",
    )
    mode_group.add_argument(
        "--all",
        action="store_true",
        help="Backward-compatible shortcut for '--mode all'",
    )

    source_group = parser.add_mutually_exclusive_group()
    source_group.add_argument(
        "--categories",
        nargs="+",
        choices=CATEGORY_CHOICES,
        help="Explicit data categories under --data-root (overrides --mode)",
    )
    source_group.add_argument(
        "--dirs",
        nargs="+",
        help="Explicit directories to ingest (overrides --mode and --categories)",
    )

    parser.add_argument(
        "--data-root",
        default=DEFAULT_DATA_ROOT,
        help=f"Root path containing ingest folders (default: {DEFAULT_DATA_ROOT})",
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively scan selected directories",
    )
    parser.add_argument(
        "--fail-on-missing",
        action="store_true",
        help="Fail instead of skipping when a selected directory is missing",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional max number of files to ingest after sorting",
    )

    args = parser.parse_args()

    if args.limit is not None and args.limit <= 0:
        parser.error("--limit must be a positive integer")

    if args.clean:
        print("=== Cleaning all document data ===")
        clean_all_data()

    target_dirs, categories, resolved_mode = _resolve_target_dirs(args)

    if categories is not None:
        print(f"=== Ingesting mode: {resolved_mode} ===")
        print(f"Categories: {', '.join(categories)}")
        print(f"Data root: {args.data_root}")
    else:
        print("=== Ingesting explicit directories ===")

    print("Directories:")
    for target_dir in target_dirs:
        print(f"  - {target_dir}")

    files = collect_files(
        target_dirs,
        recursive=args.recursive,
        fail_on_missing=args.fail_on_missing,
    )

    if args.limit is not None:
        files = files[:args.limit]
        print(f"Applying limit: {args.limit} files")

    asyncio.run(_ingest_files(files))


if __name__ == "__main__":
    main()
