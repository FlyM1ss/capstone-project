"""Batch ingest all PDFs in /data/sample-docs/"""
import asyncio
import os

from app.core.database import async_session
from app.services.ingestion import ingest_document


async def main():
    docs_dir = "/data/sample-docs"
    files = [f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx", ".pptx"))]
    print(f"Found {len(files)} documents to ingest")

    for i, filename in enumerate(files):
        path = os.path.join(docs_dir, filename)
        print(f"[{i+1}/{len(files)}] Ingesting {filename}...")
        try:
            async with async_session() as db:
                doc, chunks = await ingest_document(db, path)
                print(f"  -> {doc.title}: {chunks} chunks")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
