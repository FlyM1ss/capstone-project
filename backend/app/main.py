import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api import health, auth, documents, search
from app.core.database import async_session
from app.services.embeddings import EmbeddingServiceUnavailable
from app.services.summarizer import SummarizerUnavailable

logger = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with async_session() as db:
        await db.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary TEXT"))
        await db.execute(text("ALTER TABLE documents ADD COLUMN IF NOT EXISTS summary_generated_at TIMESTAMPTZ"))
        await db.commit()
        result = await db.execute(text("SELECT count(*) FROM documents"))
        count = result.scalar()
    logger.info("Database has %d documents", count)
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

@app.exception_handler(EmbeddingServiceUnavailable)
async def embedding_unavailable_handler(
    request: Request, exc: EmbeddingServiceUnavailable,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Embedding service is temporarily unavailable. Please try again shortly.",
            "error_code": "embedding_service_unavailable",
            "reason": exc.reason,
        },
        headers={"Retry-After": "30"},
    )


@app.exception_handler(SummarizerUnavailable)
async def summarizer_unavailable_handler(
    request: Request, exc: SummarizerUnavailable,
) -> JSONResponse:
    return JSONResponse(
        status_code=503,
        content={
            "detail": "Summary generation is temporarily unavailable.",
            "error_code": "summarizer_unavailable",
            "reason": exc.reason,
        },
    )


app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(search.router, prefix="/api", tags=["search"])
