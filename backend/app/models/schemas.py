from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Search ---
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: dict | None = None  # {"category": "policy", "access_level": "public"}
    top_k: int = Field(default=10, ge=1, le=50)
    show_latest_only: bool = True


class ChunkResult(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
    chunk_index: int
    metadata: dict = {}


class SearchResultItem(BaseModel):
    document_id: UUID
    title: str
    author: str | None
    doc_type: str
    category: str
    access_level: str
    snippet: str
    score: float
    page_count: int | None
    created_date: datetime | None
    version: int | None = None
    document_group: str | None = None


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResultItem]
    total: int
    latency_ms: int


# --- Documents ---
class DocumentOut(BaseModel):
    id: UUID
    title: str
    author: str | None
    doc_type: str
    category: str
    access_level: str
    file_path: str | None
    page_count: int | None
    chunk_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class DocumentUploadResponse(BaseModel):
    document_id: UUID
    title: str
    chunks_created: int
    status: str = "ingested"


class ChunkOut(BaseModel):
    chunk_index: int
    content: str


class DocumentChunksResponse(BaseModel):
    document_id: UUID
    chunks: list[ChunkOut]


# --- Auth ---
class UserOut(BaseModel):
    id: UUID
    email: str
    name: str | None
    role: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    email: str
    password: str
