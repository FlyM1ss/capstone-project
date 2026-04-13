import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import health, auth, documents, search
from app.api.health import ingestion_status
from app.core.database import async_session
from app.services.ingestion import ingest_document

logger = logging.getLogger("uvicorn.error")

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".pptx")
CLEAN_DIRS = ["/data/sample-docs", "/data/auxiliary"]


def _collect_files(dirs: list[str]) -> list[str]:
    """Collect all supported document files from the given directories."""
    files = []
    for docs_dir in dirs:
        if not os.path.isdir(docs_dir):
            continue
        for filename in sorted(os.listdir(docs_dir)):
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                files.append(os.path.join(docs_dir, filename))
    return files


async def _auto_ingest():
    """Background task: ingest sample documents on first startup."""
    files = _collect_files(CLEAN_DIRS)
    if not files:
        logger.warning("Auto-ingest: no document files found in %s", CLEAN_DIRS)
        return

    ingestion_status["state"] = "running"
    ingestion_status["total"] = len(files)
    logger.info("Auto-ingest: starting ingestion of %d documents", len(files))

    for i, path in enumerate(files):
        filename = os.path.basename(path)
        try:
            async with async_session() as db:
                result = await ingest_document(db, path)
                if result is None:
                    logger.info("[%d/%d] %s: SKIPPED (unchanged)", i + 1, len(files), filename)
                else:
                    _, chunk_count = result
                    logger.info("[%d/%d] %s: OK (%d chunks)", i + 1, len(files), filename, chunk_count)
        except Exception as e:
            logger.error("[%d/%d] %s: ERROR - %r", i + 1, len(files), filename, e, exc_info=True)
        ingestion_status["done"] = i + 1

    ingestion_status["state"] = "complete"
    logger.info("Auto-ingest: complete (%d/%d)", ingestion_status["done"], ingestion_status["total"])


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Check if documents table needs seeding
    async with async_session() as db:
        result = await db.execute(text("SELECT count(*) FROM documents"))
        count = result.scalar()

    if count == 0:
        logger.info("Database is empty — starting auto-ingestion in background")
        asyncio.create_task(_auto_ingest())
    else:
        logger.info("Database has %d documents — skipping auto-ingestion", count)

    yield


app = FastAPI(
    title="Deloitte AI Search Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(search.router, prefix="/api", tags=["search"])
