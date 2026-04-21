import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, Response
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db_session
from app.models.db import Document, DocumentChunk
from app.models.schemas import DocumentOut, DocumentUploadResponse, DocumentChunksResponse, ChunkOut, SummaryResponse
from app.services.ingestion import ingest_document
from app.services.pdf_conversion import get_pdf_bytes, invalidate_cache
from app.services.summarizer import generate_summary

router = APIRouter()

UPLOAD_DIR = "/data/uploads"


@router.post("/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(default=None),
    author: str = Form(default=None),
    category: str = Form(default="report"),
    access_level: str = Form(default="public"),
    db: AsyncSession = Depends(get_db_session),
):
    if not file.filename.lower().endswith((".pdf", ".docx", ".pptx")):
        raise HTTPException(status_code=400, detail="Only PDF, DOCX, PPTX files are supported")

    # Save uploaded file
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{file.filename}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    try:
        result = await ingest_document(
            db, file_path, title=title, author=author,
            category=category, access_level=access_level,
        )
        if result is None:
            raise HTTPException(status_code=409, detail="Document already exists with identical content")
        doc, chunk_count = result
        invalidate_cache(str(doc.id))
        return DocumentUploadResponse(
            document_id=doc.id, title=doc.title, chunks_created=chunk_count,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


@router.get("/documents", response_model=list[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(
            Document,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .outerjoin(DocumentChunk)
        .group_by(Document.id)
        .order_by(Document.created_at.desc())
    )
    docs = []
    for row in result.all():
        doc = row[0]
        doc_out = DocumentOut.model_validate(doc)
        doc_out.chunk_count = row[1]
        docs.append(doc_out)
    return docs


@router.get("/documents/{doc_id}", response_model=DocumentOut)
async def get_document(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(
        select(
            Document,
            func.count(DocumentChunk.id).label("chunk_count"),
        )
        .outerjoin(DocumentChunk)
        .where(Document.id == doc_id)
        .group_by(Document.id)
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Document not found")
    doc_out = DocumentOut.model_validate(row[0])
    doc_out.chunk_count = row[1]
    return doc_out


@router.get("/documents/{doc_id}/file")
async def get_document_file(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not available on disk")
    filename = os.path.basename(doc.file_path)
    media_type = "application/pdf" if doc.doc_type == "pdf" else "application/octet-stream"
    return FileResponse(
        doc.file_path,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


@router.get("/documents/{doc_id}/preview")
async def get_document_preview(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    if not doc.file_path or not os.path.exists(doc.file_path):
        raise HTTPException(status_code=404, detail="File not available on disk")
    try:
        pdf_bytes = await get_pdf_bytes(str(doc.id), doc.file_path, doc.doc_type, settings.GOTENBERG_URL)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"PDF conversion failed: {e}")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{doc_id}.pdf"'},
    )


@router.get("/documents/{doc_id}/chunks", response_model=DocumentChunksResponse)
async def get_document_chunks(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    doc_result = await db.execute(select(Document).where(Document.id == doc_id))
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")
    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = chunks_result.scalars().all()
    return DocumentChunksResponse(
        document_id=doc_id,
        chunks=[ChunkOut(chunk_index=c.chunk_index, content=c.content) for c in chunks],
    )


@router.get("/documents/{doc_id}/summary", response_model=SummaryResponse)
async def get_document_summary(doc_id: uuid.UUID, db: AsyncSession = Depends(get_db_session)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    if doc.summary:
        return SummaryResponse(
            document_id=doc.id,
            summary=doc.summary,
            cached=True,
            generated_at=doc.summary_generated_at,
        )

    chunks_result = await db.execute(
        select(DocumentChunk)
        .where(DocumentChunk.document_id == doc_id)
        .order_by(DocumentChunk.chunk_index)
    )
    chunks = list(chunks_result.scalars().all())

    summary_text: str | None = None
    now: datetime | None = None
    if chunks:
        summary_text = await generate_summary(doc, chunks)
        now = datetime.now(timezone.utc)
        doc.summary = summary_text
        doc.summary_generated_at = now
        await db.commit()

    return SummaryResponse(
        document_id=doc.id, summary=summary_text, cached=False, generated_at=now,
    )
