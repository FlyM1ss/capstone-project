import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.db import Document, DocumentChunk
from app.models.schemas import DocumentOut, DocumentUploadResponse
from app.services.ingestion import ingest_document

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
        doc, chunk_count = await ingest_document(
            db, file_path, title=title, author=author,
            category=category, access_level=access_level,
        )
        return DocumentUploadResponse(
            document_id=doc.id, title=doc.title, chunks_created=chunk_count,
        )
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
