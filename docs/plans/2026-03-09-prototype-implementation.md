# Deloitte AI Search Engine — Prototype Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a demo-ready MVP of the Deloitte AI Search Engine with hybrid search, document ingestion, admin upload portal, and role-based access.

**Architecture:** Monorepo with Docker Compose (3 containers: frontend, backend, db). Embedding model hosted on Google Colab via ngrok. FastAPI backend orchestrates hybrid search (pgvector semantic + ParadeDB BM25), RRF merge, and Cohere reranking. Next.js 15 frontend with shadcn/ui.

**Tech Stack:** Next.js 15 (App Router), TypeScript, shadcn/ui, Vercel AI SDK, FastAPI, Python 3.11+, PostgreSQL 16 (ParadeDB image w/ pgvector + pg_search), Docling, Cohere Rerank 4, Qwen3-Embedding-0.6B, NextAuth.js, Docker Compose.

**Design doc:** `docs/plans/2026-03-09-prototype-mvp-design.md`

---

## Prerequisites

- Docker Desktop installed with WSL 2 integration enabled
- Node.js 20+ (already have v24)
- Python 3.11+ (have 3.10 — upgrade or use Docker for backend)
- Cohere API key (free tier: https://dashboard.cohere.com/api-keys)
- Google account for Colab notebook

---

## Phase 1: Project Infrastructure

### Task 1: Create directory structure

**Files:**
- Create: `frontend/.gitkeep`
- Create: `backend/app/__init__.py`
- Create: `backend/requirements.txt`
- Create: `.env.example`
- Modify: `.gitignore`

**Step 1: Create directories**

```bash
cd /mnt/c/Users/27740/OneDrive/Documents/RPI/capstone-project
mkdir -p frontend backend/app/api backend/app/core backend/app/models backend/app/services
mkdir -p backend/tests data/sample-docs
touch backend/app/__init__.py backend/app/api/__init__.py backend/app/core/__init__.py
touch backend/app/models/__init__.py backend/app/services/__init__.py
touch backend/tests/__init__.py
```

**Step 2: Create `.env.example`**

```env
# Database
POSTGRES_USER=deloitte
POSTGRES_PASSWORD=deloitte_dev
POSTGRES_DB=search_engine
DATABASE_URL=postgresql+asyncpg://deloitte:deloitte_dev@db:5432/search_engine

# Embedding service
EMBEDDING_API_URL=http://localhost:8001/embed

# Cohere
COHERE_API_KEY=your_cohere_api_key_here

# NextAuth
NEXTAUTH_SECRET=your_nextauth_secret_here
NEXTAUTH_URL=http://localhost:3000

# Backend
BACKEND_URL=http://localhost:8000
```

**Step 3: Update `.gitignore`** — add `!data/sample-docs/` so demo PDFs are tracked:

```gitignore
# after existing data/ line, add:
!data/sample-docs/
!data/sample-docs/**
```

**Step 4: Create `backend/requirements.txt`**

```txt
fastapi==0.115.12
uvicorn[standard]==0.34.2
sqlalchemy[asyncio]==2.0.41
asyncpg==0.30.0
pgvector==0.3.6
pydantic-settings==2.9.1
python-multipart==0.0.20
docling==2.31.0
cohere==5.15.0
httpx==0.28.1
python-jose[cryptography]==3.4.0
passlib[bcrypt]==1.7.4
```

**Step 5: Commit**

```bash
git add -A
git commit -m "chore: scaffold project directory structure"
```

---

### Task 2: Create Docker Compose configuration

**Files:**
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`
- Create: `frontend/Dockerfile`

**Step 1: Create `docker-compose.yml`**

```yaml
services:
  db:
    image: paradedb/paradedb:latest
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-deloitte}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-deloitte_dev}
      POSTGRES_DB: ${POSTGRES_DB:-search_engine}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./backend/db/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U deloitte -d search_engine"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-deloitte}:${POSTGRES_PASSWORD:-deloitte_dev}@db:5432/${POSTGRES_DB:-search_engine}
      EMBEDDING_API_URL: ${EMBEDDING_API_URL:-http://host.docker.internal:8001/embed}
      COHERE_API_KEY: ${COHERE_API_KEY}
    volumes:
      - ./backend:/app
      - ./data:/data
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      NEXT_PUBLIC_API_URL: http://localhost:8000
      NEXTAUTH_SECRET: ${NEXTAUTH_SECRET:-dev_secret_change_me}
      NEXTAUTH_URL: http://localhost:3000
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - backend

volumes:
  pgdata:
```

**Step 2: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

**Step 3: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

CMD ["npm", "run", "dev"]
```

**Step 4: Commit**

```bash
git add docker-compose.yml backend/Dockerfile frontend/Dockerfile
git commit -m "chore: add Docker Compose with ParadeDB, backend, frontend"
```

---

## Phase 2: Database Setup

### Task 3: Create database initialization script

**Files:**
- Create: `backend/db/init.sql`

**Step 1: Create `backend/db/init.sql`**

```sql
-- Extensions (ParadeDB image has these available)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;        -- pgvector
CREATE EXTENSION IF NOT EXISTS pg_search;     -- ParadeDB BM25

-- Documents table
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title TEXT NOT NULL,
    author TEXT,
    doc_type TEXT DEFAULT 'pdf',
    category TEXT DEFAULT 'report',
    created_date TIMESTAMPTZ,
    access_level TEXT DEFAULT 'public' CHECK (access_level IN ('public', 'internal', 'confidential')),
    file_path TEXT,
    page_count INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Document chunks with embeddings
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    hashed_password TEXT NOT NULL,
    role TEXT DEFAULT 'analyst' CHECK (role IN ('analyst', 'manager', 'admin')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Query logs
CREATE TABLE IF NOT EXISTS query_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    query_text TEXT,
    result_count INTEGER,
    selected_doc_id UUID,
    latency_ms INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- pgvector index for semantic search (HNSW for speed)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding
    ON document_chunks
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Standard indexes
CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_documents_access_level ON documents(access_level);
CREATE INDEX IF NOT EXISTS idx_documents_category ON documents(category);
CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);

-- Seed demo users
INSERT INTO users (email, name, hashed_password, role) VALUES
    ('admin@deloitte.com', 'Admin User', '$2b$12$LJ3m4ys3Lk0YGFQhKEBzfOWMiR8JRjGjC1y6iYqDBsXcJx3wqFBi', 'admin'),
    ('manager@deloitte.com', 'Manager User', '$2b$12$LJ3m4ys3Lk0YGFQhKEBzfOWMiR8JRjGjC1y6iYqDBsXcJx3wqFBi', 'manager'),
    ('analyst@deloitte.com', 'Analyst User', '$2b$12$LJ3m4ys3Lk0YGFQhKEBzfOWMiR8JRjGjC1y6iYqDBsXcJx3wqFBi', 'analyst')
ON CONFLICT (email) DO NOTHING;
-- All demo passwords: "password123"

-- NOTE: ParadeDB BM25 index is created AFTER data is ingested
-- because it needs at least one row. See backend ingestion service.
```

**Step 2: Commit**

```bash
mkdir -p backend/db
git add backend/db/init.sql
git commit -m "feat: add database schema with pgvector + ParadeDB setup"
```

---

### Task 4: Create SQLAlchemy models and database connection

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/database.py`
- Create: `backend/app/models/db.py`
- Create: `backend/app/models/schemas.py`

**Step 1: Create `backend/app/core/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://deloitte:deloitte_dev@localhost:5432/search_engine"
    EMBEDDING_API_URL: str = "http://localhost:8001/embed"
    COHERE_API_KEY: str = ""

    # Search tuning
    SEARCH_TOP_K: int = 50
    RERANK_TOP_N: int = 10
    RRF_K: int = 60
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    class Config:
        env_file = ".env"


settings = Settings()
```

**Step 2: Create `backend/app/core/database.py`**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from app.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
```

**Step 3: Create `backend/app/models/db.py`**

```python
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector


class Base(DeclarativeBase):
    pass


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String(20), default="pdf")
    category: Mapped[str] = mapped_column(String(50), default="report")
    created_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    access_level: Mapped[str] = mapped_column(String(20), default="public")
    file_path: Mapped[str | None] = mapped_column(Text)
    page_count: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    chunks: Mapped[list["DocumentChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding = mapped_column(Vector(1024))
    metadata_: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    document: Mapped["Document"] = relationship(back_populates="chunks")


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    name: Mapped[str | None] = mapped_column(Text)
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(20), default="analyst")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class QueryLog(Base):
    __tablename__ = "query_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    query_text: Mapped[str | None] = mapped_column(Text)
    result_count: Mapped[int | None] = mapped_column(Integer)
    selected_doc_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
```

**Step 4: Create `backend/app/models/schemas.py`**

```python
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Search ---
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    filters: dict | None = None  # {"category": "policy", "access_level": "public"}
    top_k: int = Field(default=10, ge=1, le=50)


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
```

**Step 5: Commit**

```bash
git add backend/app/core/ backend/app/models/
git commit -m "feat: add database config, SQLAlchemy models, Pydantic schemas"
```

---

## Phase 3: Backend API Foundation

### Task 5: Create FastAPI application with health endpoint

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/api/health.py`
- Create: `backend/app/core/deps.py`

**Step 1: Create `backend/app/core/deps.py`**

```python
from app.core.database import get_db

# Re-export; central place for dependency injection
get_db_session = get_db
```

**Step 2: Create `backend/app/api/health.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db_session)):
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return {"status": "ok", "database": db_status}
```

**Step 3: Create `backend/app/main.py`**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown


app = FastAPI(
    title="Deloitte AI Search Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
```

**Step 4: Test — start Docker Compose and verify health endpoint**

```bash
cp .env.example .env  # fill in COHERE_API_KEY
docker compose up -d db backend
curl http://localhost:8000/api/health
# Expected: {"status":"ok","database":"connected"}
```

**Step 5: Commit**

```bash
git add backend/app/main.py backend/app/api/health.py backend/app/core/deps.py
git commit -m "feat: FastAPI app with health endpoint and DB connection"
```

---

### Task 6: Create auth endpoints and password utilities

**Files:**
- Create: `backend/app/api/auth.py`
- Create: `backend/app/services/auth.py`

**Step 1: Create `backend/app/services/auth.py`**

```python
from datetime import datetime, timedelta

from jose import jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.db import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SECRET_KEY = "dev-secret-key-change-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user and verify_password(password, user.hashed_password):
        return user
    return None


async def get_user_from_token(db: AsyncSession, token: str) -> User | None:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            return None
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    except Exception:
        return None
```

**Step 2: Create `backend/app/api/auth.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.schemas import LoginRequest, UserOut
from app.services.auth import authenticate_user, create_access_token

router = APIRouter()


@router.post("/auth/login")
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db_session)):
    user = await authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token({"sub": str(user.id), "role": user.role})
    return {"access_token": token, "token_type": "bearer", "user": UserOut.model_validate(user)}
```

**Step 3: Register in `main.py`**

Add to `backend/app/main.py`:
```python
from app.api import health, auth
# ...
app.include_router(auth.router, prefix="/api", tags=["auth"])
```

**Step 4: Commit**

```bash
git add backend/app/api/auth.py backend/app/services/auth.py backend/app/main.py
git commit -m "feat: add JWT auth with login endpoint"
```

---

## Phase 4: Embedding Service (Colab Notebook)

### Task 7: Create Google Colab embedding server notebook

**Files:**
- Create: `notebooks/embedding_server.ipynb` (or provide code for manual Colab setup)
- Create: `backend/app/services/embeddings.py`

**Step 1: Create embedding client in backend**

Create `backend/app/services/embeddings.py`:

```python
import httpx

from app.core.config import settings


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Call the embedding service (Colab or local) to generate vectors."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            settings.EMBEDDING_API_URL,
            json={"texts": texts},
        )
        response.raise_for_status()
        return response.json()["embeddings"]


async def generate_embedding(text: str) -> list[float]:
    """Generate a single embedding."""
    results = await generate_embeddings([text])
    return results[0]
```

**Step 2: Create Colab notebook code**

Save to `notebooks/README.md` with the following instructions and code to paste into Colab:

```markdown
# Embedding Server (Google Colab)

1. Open Google Colab (https://colab.research.google.com)
2. Select GPU runtime: Runtime → Change runtime type → T4 GPU
3. Paste the code below into a cell and run it
4. Copy the ngrok URL and set it as EMBEDDING_API_URL in your .env

## Code

​```python
# Cell 1: Install dependencies
!pip install sentence-transformers fastapi uvicorn pyngrok

# Cell 2: Start server
import torch
from sentence_transformers import SentenceTransformer
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn
import threading
from pyngrok import ngrok

# Load model (downloads ~1.2GB first time)
model = SentenceTransformer("Qwen/Qwen3-Embedding-0.6B", trust_remote_code=True)
model.to("cuda" if torch.cuda.is_available() else "cpu")
print(f"Model loaded on {model.device}")

app = FastAPI()

class EmbedRequest(BaseModel):
    texts: list[str]

@app.post("/embed")
async def embed(req: EmbedRequest):
    embeddings = model.encode(req.texts, normalize_embeddings=True)
    return {"embeddings": embeddings.tolist()}

@app.get("/health")
async def health():
    return {"status": "ok", "model": "Qwen3-Embedding-0.6B", "device": str(model.device)}

# Start ngrok tunnel
public_url = ngrok.connect(8001)
print(f"\n✅ Embedding server ready!")
print(f"📋 Set this in your .env:")
print(f"EMBEDDING_API_URL={public_url}/embed\n")

# Run server
uvicorn.run(app, host="0.0.0.0", port=8001)
​```

Note: You need a free ngrok auth token. Get one at https://dashboard.ngrok.com/signup
then run: `!ngrok authtoken YOUR_TOKEN` before starting the server.
```

**Step 3: Commit**

```bash
mkdir -p notebooks
git add notebooks/README.md backend/app/services/embeddings.py
git commit -m "feat: add embedding service client and Colab server instructions"
```

---

## Phase 5: Document Ingestion Pipeline

### Task 8: Create ingestion service

**Files:**
- Create: `backend/app/services/ingestion.py`
- Create: `backend/app/api/documents.py`

**Step 1: Create `backend/app/services/ingestion.py`**

```python
import uuid
from pathlib import Path

from docling.document_converter import DocumentConverter
from sqlalchemy import text, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db import Document, DocumentChunk
from app.services.embeddings import generate_embeddings


def chunk_text(text_content: str, chunk_size: int = 512, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by word count."""
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


async def ingest_document(
    db: AsyncSession,
    file_path: str,
    title: str | None = None,
    author: str | None = None,
    category: str = "report",
    access_level: str = "public",
) -> tuple[Document, int]:
    """Parse a PDF, chunk it, embed chunks, and store everything."""
    # 1. Parse with Docling
    converter = DocumentConverter()
    result = converter.convert(file_path)
    full_text = result.document.export_to_markdown()

    # Infer title from first line if not provided
    if not title:
        first_line = full_text.strip().split("\n")[0]
        title = first_line.strip("# ").strip()[:200] or Path(file_path).stem

    # 2. Create document record
    doc = Document(
        title=title,
        author=author,
        doc_type=Path(file_path).suffix.lstrip("."),
        category=category,
        access_level=access_level,
        file_path=file_path,
        page_count=getattr(result.document, "num_pages", None),
    )
    db.add(doc)
    await db.flush()  # Get doc.id

    # 3. Chunk text
    chunks = chunk_text(full_text)
    if not chunks:
        await db.commit()
        return doc, 0

    # 4. Generate embeddings (batch)
    embeddings = await generate_embeddings(chunks)

    # 5. Store chunks with embeddings
    for i, (chunk_text_content, embedding) in enumerate(zip(chunks, embeddings)):
        chunk = DocumentChunk(
            document_id=doc.id,
            chunk_index=i,
            content=chunk_text_content,
            embedding=embedding,
        )
        db.add(chunk)

    await db.commit()

    # 6. Ensure ParadeDB BM25 index exists
    await _ensure_bm25_index(db)

    return doc, len(chunks)


async def _ensure_bm25_index(db: AsyncSession):
    """Create ParadeDB BM25 index if it doesn't exist."""
    try:
        await db.execute(text("""
            CALL paradedb.create_bm25(
                index_name => 'idx_chunks_bm25',
                table_name => 'document_chunks',
                key_field => 'id',
                text_fields => paradedb.field('content')
            )
        """))
        await db.commit()
    except Exception:
        # Index may already exist
        await db.rollback()
```

**Step 2: Create `backend/app/api/documents.py`**

```python
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
```

**Step 3: Register in `main.py`**

Add to `backend/app/main.py`:
```python
from app.api import health, auth, documents
# ...
app.include_router(documents.router, prefix="/api", tags=["documents"])
```

**Step 4: Commit**

```bash
git add backend/app/services/ingestion.py backend/app/api/documents.py backend/app/main.py
git commit -m "feat: add document ingestion pipeline with Docling + chunking + embedding"
```

---

## Phase 6: Search Pipeline

### Task 9: Create hybrid search service

**Files:**
- Create: `backend/app/services/search.py`
- Create: `backend/app/services/reranker.py`
- Create: `backend/app/api/search.py`

**Step 1: Create `backend/app/services/search.py`**

```python
import time
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.schemas import SearchResultItem
from app.services.embeddings import generate_embedding
from app.services.reranker import rerank_results


async def hybrid_search(
    db: AsyncSession,
    query: str,
    filters: dict | None = None,
    user_role: str = "analyst",
    top_k: int = 10,
) -> tuple[list[SearchResultItem], int]:
    """Execute hybrid search: semantic + BM25, RRF merge, rerank."""
    start = time.time()

    # 1. Generate query embedding
    query_embedding = await generate_embedding(query)

    # 2. Build access level filter
    access_levels = _get_access_levels(user_role)
    access_filter = ", ".join(f"'{a}'" for a in access_levels)

    # 3. Semantic search (pgvector cosine similarity)
    semantic_sql = text(f"""
        SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
               1 - (dc.embedding <=> :embedding::vector) AS score
        FROM document_chunks dc
        JOIN documents d ON dc.document_id = d.id
        WHERE d.access_level IN ({access_filter})
        ORDER BY dc.embedding <=> :embedding::vector
        LIMIT :top_k
    """)
    semantic_result = await db.execute(
        semantic_sql,
        {"embedding": str(query_embedding), "top_k": settings.SEARCH_TOP_K},
    )
    semantic_rows = semantic_result.fetchall()

    # 4. BM25 keyword search (ParadeDB)
    bm25_rows = []
    try:
        bm25_sql = text(f"""
            SELECT dc.id, dc.document_id, dc.content, dc.chunk_index,
                   paradedb.score(dc.id) AS score
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.id @@@ paradedb.parse(:query)
              AND d.access_level IN ({access_filter})
            ORDER BY paradedb.score(dc.id) DESC
            LIMIT :top_k
        """)
        bm25_result = await db.execute(
            bm25_sql, {"query": query, "top_k": settings.SEARCH_TOP_K},
        )
        bm25_rows = bm25_result.fetchall()
    except Exception:
        # BM25 index may not exist yet (no docs ingested)
        pass

    # 5. Reciprocal Rank Fusion
    merged = _rrf_merge(semantic_rows, bm25_rows, k=settings.RRF_K)

    if not merged:
        latency_ms = int((time.time() - start) * 1000)
        return [], latency_ms

    # 6. Rerank with Cohere
    top_chunks = merged[:settings.SEARCH_TOP_K]
    chunk_texts = [c["content"] for c in top_chunks]
    chunk_ids = [c["id"] for c in top_chunks]

    reranked_indices = await rerank_results(query, chunk_texts, top_n=top_k)

    # 7. Build final results (group by document)
    seen_docs = set()
    results = []
    for idx in reranked_indices:
        chunk = top_chunks[idx]
        doc_id = chunk["document_id"]
        if doc_id in seen_docs:
            continue
        seen_docs.add(doc_id)

        # Fetch document metadata
        doc_sql = text("SELECT * FROM documents WHERE id = :doc_id")
        doc_row = (await db.execute(doc_sql, {"doc_id": doc_id})).fetchone()
        if doc_row:
            results.append(SearchResultItem(
                document_id=doc_row.id,
                title=doc_row.title,
                author=doc_row.author,
                doc_type=doc_row.doc_type,
                category=doc_row.category,
                access_level=doc_row.access_level,
                snippet=chunk["content"][:300],
                score=chunk["rrf_score"],
                page_count=doc_row.page_count,
                created_date=doc_row.created_date,
            ))

    latency_ms = int((time.time() - start) * 1000)
    return results, latency_ms


def _get_access_levels(role: str) -> list[str]:
    if role == "admin":
        return ["public", "internal", "confidential"]
    elif role == "manager":
        return ["public", "internal"]
    return ["public"]


def _rrf_merge(semantic_rows, bm25_rows, k: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion: combine two ranked lists."""
    scores: dict[str, dict] = {}

    for rank, row in enumerate(semantic_rows):
        chunk_id = str(row.id)
        if chunk_id not in scores:
            scores[chunk_id] = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "rrf_score": 0.0,
            }
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    for rank, row in enumerate(bm25_rows):
        chunk_id = str(row.id)
        if chunk_id not in scores:
            scores[chunk_id] = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "chunk_index": row.chunk_index,
                "rrf_score": 0.0,
            }
        scores[chunk_id]["rrf_score"] += 1.0 / (k + rank + 1)

    merged = sorted(scores.values(), key=lambda x: x["rrf_score"], reverse=True)
    return merged
```

**Step 2: Create `backend/app/services/reranker.py`**

```python
import cohere

from app.core.config import settings


async def rerank_results(query: str, texts: list[str], top_n: int = 10) -> list[int]:
    """Rerank texts using Cohere Rerank and return indices of top results."""
    if not settings.COHERE_API_KEY or not texts:
        return list(range(min(top_n, len(texts))))

    try:
        co = cohere.Client(settings.COHERE_API_KEY)
        response = co.rerank(
            model="rerank-v3.5",
            query=query,
            documents=texts,
            top_n=top_n,
        )
        return [r.index for r in response.results]
    except Exception:
        # Fallback: return original order
        return list(range(min(top_n, len(texts))))
```

**Step 3: Create `backend/app/api/search.py`**

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db_session
from app.models.schemas import SearchRequest, SearchResponse
from app.services.search import hybrid_search
from app.services.validation import validate_query

router = APIRouter()


@router.post("/search", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    db: AsyncSession = Depends(get_db_session),
):
    # Validate input
    validate_query(body.query)

    # TODO: extract user role from auth token; default to analyst for now
    user_role = "admin"  # permissive for demo

    results, latency_ms = await hybrid_search(
        db, body.query, filters=body.filters,
        user_role=user_role, top_k=body.top_k,
    )

    return SearchResponse(
        query=body.query,
        results=results,
        total=len(results),
        latency_ms=latency_ms,
    )
```

**Step 4: Create `backend/app/services/validation.py`**

```python
import re

from fastapi import HTTPException


def validate_query(query: str) -> None:
    """Validate search query: length, content, injection patterns."""
    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    if len(query) > 500:
        raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")

    # Block obvious prompt injection patterns
    injection_patterns = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"system\s*prompt",
        r"you\s+are\s+now",
        r"<\s*script",
    ]
    for pattern in injection_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            raise HTTPException(status_code=400, detail="Query contains disallowed patterns")
```

**Step 5: Register in `main.py`**

Add to `backend/app/main.py`:
```python
from app.api import health, auth, documents, search
# ...
app.include_router(search.router, prefix="/api", tags=["search"])
```

**Step 6: Commit**

```bash
git add backend/app/services/search.py backend/app/services/reranker.py \
        backend/app/services/validation.py backend/app/api/search.py backend/app/main.py
git commit -m "feat: add hybrid search pipeline with RRF merge and Cohere reranking"
```

---

## Phase 7: Frontend Foundation

### Task 10: Initialize Next.js project with shadcn/ui

**Step 1: Create Next.js app**

```bash
cd /mnt/c/Users/27740/OneDrive/Documents/RPI/capstone-project/frontend
npx create-next-app@latest . --typescript --tailwind --eslint --app --src-dir=no \
    --import-alias="@/*" --use-npm
```

**Step 2: Install shadcn/ui**

```bash
npx shadcn@latest init -d
npx shadcn@latest add button card input badge separator sheet scroll-area
```

**Step 3: Install additional dependencies**

```bash
npm install ai @ai-sdk/react next-auth lucide-react
```

**Step 4: Create API client**

Create `frontend/lib/api.ts`:

```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface SearchResult {
  document_id: string;
  title: string;
  author: string | null;
  doc_type: string;
  category: string;
  access_level: string;
  snippet: string;
  score: number;
  page_count: number | null;
  created_date: string | null;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total: number;
  latency_ms: number;
}

export async function searchDocuments(
  query: string,
  filters?: Record<string, string>,
): Promise<SearchResponse> {
  const res = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, filters }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Search failed");
  }
  return res.json();
}

export interface DocumentInfo {
  id: string;
  title: string;
  author: string | null;
  doc_type: string;
  category: string;
  access_level: string;
  chunk_count: number;
  created_at: string;
}

export async function listDocuments(): Promise<DocumentInfo[]> {
  const res = await fetch(`${API_URL}/api/documents`);
  if (!res.ok) throw new Error("Failed to fetch documents");
  return res.json();
}

export async function uploadDocument(formData: FormData): Promise<void> {
  const res = await fetch(`${API_URL}/api/documents`, {
    method: "POST",
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
}
```

**Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: initialize Next.js 15 with shadcn/ui and API client"
```

---

### Task 11: Build landing page with search bar

**Files:**
- Create: `frontend/components/search-bar.tsx`
- Create: `frontend/components/search-tips.tsx`
- Modify: `frontend/app/page.tsx`
- Modify: `frontend/app/layout.tsx`

**Step 1: Create `frontend/components/search-bar.tsx`**

```tsx
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { SearchTips } from "./search-tips";

export function SearchBar({ defaultValue = "" }: { defaultValue?: string }) {
  const [query, setQuery] = useState(defaultValue);
  const router = useRouter();

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      router.push(`/search?q=${encodeURIComponent(query.trim())}`);
    }
  };

  return (
    <form onSubmit={handleSearch} className="relative w-full max-w-2xl">
      <div className="relative flex items-center">
        <Search className="absolute left-3 h-5 w-5 text-muted-foreground" />
        <Input
          type="text"
          placeholder="Search Deloitte resources..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          className="pl-10 pr-20 h-12 text-base"
        />
        <div className="absolute right-2 flex items-center gap-1">
          <SearchTips />
          <Button type="submit" size="sm" disabled={!query.trim()}>
            Search
          </Button>
        </div>
      </div>
    </form>
  );
}
```

**Step 2: Create `frontend/components/search-tips.tsx`**

```tsx
"use client";

import { useState } from "react";
import { Info, X } from "lucide-react";
import { Button } from "@/components/ui/button";

export function SearchTips() {
  const [open, setOpen] = useState(false);

  return (
    <div className="relative">
      <Button
        type="button"
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => setOpen(!open)}
        aria-label="Search tips"
      >
        {open ? <X className="h-4 w-4" /> : <Info className="h-4 w-4" />}
      </Button>

      {open && (
        <div className="absolute right-0 top-10 z-50 w-80 rounded-lg border bg-card p-4 shadow-lg">
          <h4 className="mb-2 font-semibold text-sm">Search Tips</h4>
          <ul className="space-y-1.5 text-sm text-muted-foreground">
            <li>Use natural language: <span className="text-foreground">"Q4 healthcare consulting deck"</span></li>
            <li>Search by topic: <span className="text-foreground">"travel reimbursement policy"</span></li>
            <li>Find by type: <span className="text-foreground">"annual financial report with charts"</span></li>
            <li>Search by author: <span className="text-foreground">"presentation by marketing team"</span></li>
          </ul>
        </div>
      )}
    </div>
  );
}
```

**Step 3: Update `frontend/app/page.tsx`**

```tsx
import { SearchBar } from "@/components/search-bar";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center px-4">
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold tracking-tight mb-2">
          Deloitte Search
        </h1>
        <p className="text-muted-foreground">
          Find internal resources using natural language
        </p>
      </div>
      <SearchBar />
      <div className="mt-6 flex gap-2 flex-wrap justify-center">
        {["Q4 consulting deck", "travel policy", "annual report 2025"].map((example) => (
          <a
            key={example}
            href={`/search?q=${encodeURIComponent(example)}`}
            className="rounded-full border px-3 py-1 text-sm text-muted-foreground hover:text-foreground hover:border-foreground transition-colors"
          >
            {example}
          </a>
        ))}
      </div>
    </main>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/components/ frontend/app/page.tsx
git commit -m "feat: add landing page with search bar and search tips"
```

---

### Task 12: Build search results page

**Files:**
- Create: `frontend/components/result-card.tsx`
- Create: `frontend/components/search-results.tsx`
- Create: `frontend/components/filter-panel.tsx`
- Create: `frontend/app/search/page.tsx`

**Step 1: Create `frontend/components/result-card.tsx`**

```tsx
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { FileText, User, Calendar } from "lucide-react";
import type { SearchResult } from "@/lib/api";

const categoryColors: Record<string, string> = {
  policy: "bg-blue-100 text-blue-800",
  report: "bg-green-100 text-green-800",
  deck: "bg-purple-100 text-purple-800",
  memo: "bg-orange-100 text-orange-800",
};

export function ResultCard({ result }: { result: SearchResult }) {
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer">
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <CardTitle className="text-base leading-snug">{result.title}</CardTitle>
          <Badge variant="outline" className={categoryColors[result.category] || ""}>
            {result.category}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground line-clamp-3 mb-3">
          {result.snippet}
        </p>
        <div className="flex items-center gap-4 text-xs text-muted-foreground">
          {result.author && (
            <span className="flex items-center gap-1">
              <User className="h-3 w-3" /> {result.author}
            </span>
          )}
          {result.created_date && (
            <span className="flex items-center gap-1">
              <Calendar className="h-3 w-3" />
              {new Date(result.created_date).toLocaleDateString()}
            </span>
          )}
          <span className="flex items-center gap-1">
            <FileText className="h-3 w-3" /> {result.doc_type.toUpperCase()}
          </span>
          {result.page_count && (
            <span>{result.page_count} pages</span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
```

**Step 2: Create `frontend/components/filter-panel.tsx`**

```tsx
"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

interface FilterPanelProps {
  filters: Record<string, string>;
  onFilterChange: (filters: Record<string, string>) => void;
}

const categories = ["policy", "report", "deck", "memo"];
const docTypes = ["pdf", "docx", "pptx"];

export function FilterPanel({ filters, onFilterChange }: FilterPanelProps) {
  const toggleFilter = (key: string, value: string) => {
    const updated = { ...filters };
    if (updated[key] === value) {
      delete updated[key];
    } else {
      updated[key] = value;
    }
    onFilterChange(updated);
  };

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-semibold mb-2">Category</h3>
        <div className="flex flex-col gap-1">
          {categories.map((cat) => (
            <Button
              key={cat}
              variant={filters.category === cat ? "default" : "ghost"}
              size="sm"
              className="justify-start capitalize"
              onClick={() => toggleFilter("category", cat)}
            >
              {cat}
            </Button>
          ))}
        </div>
      </div>
      <div>
        <h3 className="text-sm font-semibold mb-2">File Type</h3>
        <div className="flex flex-col gap-1">
          {docTypes.map((dt) => (
            <Button
              key={dt}
              variant={filters.doc_type === dt ? "default" : "ghost"}
              size="sm"
              className="justify-start uppercase"
              onClick={() => toggleFilter("doc_type", dt)}
            >
              {dt}
            </Button>
          ))}
        </div>
      </div>
      {Object.keys(filters).length > 0 && (
        <Button
          variant="outline"
          size="sm"
          className="w-full"
          onClick={() => onFilterChange({})}
        >
          Clear Filters
        </Button>
      )}
    </div>
  );
}
```

**Step 3: Create `frontend/app/search/page.tsx`**

```tsx
"use client";

import { useSearchParams } from "next/navigation";
import { useEffect, useState, Suspense } from "react";
import { SearchBar } from "@/components/search-bar";
import { ResultCard } from "@/components/result-card";
import { FilterPanel } from "@/components/filter-panel";
import { searchDocuments, type SearchResponse } from "@/lib/api";

function SearchContent() {
  const searchParams = useSearchParams();
  const query = searchParams.get("q") || "";
  const [response, setResponse] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Record<string, string>>({});

  useEffect(() => {
    if (!query) return;
    setLoading(true);
    setError(null);
    searchDocuments(query, Object.keys(filters).length > 0 ? filters : undefined)
      .then(setResponse)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query, filters]);

  return (
    <div className="min-h-screen">
      <header className="border-b px-6 py-4">
        <div className="flex items-center gap-4 max-w-5xl mx-auto">
          <a href="/" className="text-xl font-bold whitespace-nowrap">
            Deloitte Search
          </a>
          <SearchBar defaultValue={query} />
        </div>
      </header>

      <div className="max-w-5xl mx-auto px-6 py-6 flex gap-6">
        <aside className="w-48 shrink-0 hidden md:block">
          <FilterPanel filters={filters} onFilterChange={setFilters} />
        </aside>

        <main className="flex-1">
          {loading && <p className="text-muted-foreground">Searching...</p>}
          {error && <p className="text-destructive">{error}</p>}
          {response && !loading && (
            <>
              <p className="text-sm text-muted-foreground mb-4">
                {response.total} results in {response.latency_ms}ms
              </p>
              {response.results.length === 0 ? (
                <div className="text-center py-12">
                  <p className="text-lg font-medium mb-2">No results found</p>
                  <p className="text-sm text-muted-foreground">
                    Try different keywords or remove filters
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {response.results.map((result) => (
                    <ResultCard key={result.document_id} result={result} />
                  ))}
                </div>
              )}
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense fallback={<p>Loading...</p>}>
      <SearchContent />
    </Suspense>
  );
}
```

**Step 4: Commit**

```bash
git add frontend/components/ frontend/app/search/
git commit -m "feat: add search results page with filters and result cards"
```

---

## Phase 8: Admin Upload Portal

### Task 13: Build admin upload page

**Files:**
- Create: `frontend/app/admin/upload/page.tsx`
- Create: `frontend/components/file-upload.tsx`

**Step 1: Create `frontend/components/file-upload.tsx`**

```tsx
"use client";

import { useState, useCallback } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { uploadDocument } from "@/lib/api";

interface FileStatus {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  message?: string;
}

export function FileUpload({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [files, setFiles] = useState<FileStatus[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const pdfFiles = Array.from(newFiles).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf") ||
      f.name.toLowerCase().endsWith(".docx") ||
      f.name.toLowerCase().endsWith(".pptx")
    );
    setFiles((prev) => [
      ...prev,
      ...pdfFiles.map((file) => ({ file, status: "pending" as const })),
    ]);
  };

  const handleUpload = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== "pending") continue;

      setFiles((prev) =>
        prev.map((f, idx) => (idx === i ? { ...f, status: "uploading" } : f))
      );

      try {
        const formData = new FormData();
        formData.append("file", files[i].file);
        await uploadDocument(formData);
        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "done", message: "Ingested" } : f))
        );
      } catch (e: any) {
        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "error", message: e.message } : f))
        );
      }
    }
    onUploadComplete();
  };

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
      >
        <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground mb-2">
          Drag & drop PDFs here, or{" "}
          <label className="text-primary cursor-pointer underline">
            browse
            <input type="file" className="hidden" multiple accept=".pdf,.docx,.pptx"
              onChange={(e) => addFiles(e.target.files)} />
          </label>
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, i) => (
            <Card key={i}>
              <CardContent className="flex items-center gap-3 py-3 px-4">
                <FileText className="h-4 w-4 shrink-0" />
                <span className="text-sm flex-1 truncate">{f.file.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(f.file.size / 1024).toFixed(0)} KB
                </span>
                {f.status === "uploading" && <Loader2 className="h-4 w-4 animate-spin" />}
                {f.status === "done" && <CheckCircle className="h-4 w-4 text-green-500" />}
                {f.status === "error" && <AlertCircle className="h-4 w-4 text-destructive" />}
              </CardContent>
            </Card>
          ))}
          <Button onClick={handleUpload} disabled={files.every((f) => f.status !== "pending")}>
            Upload & Ingest ({files.filter((f) => f.status === "pending").length} files)
          </Button>
        </div>
      )}
    </div>
  );
}
```

**Step 2: Create `frontend/app/admin/upload/page.tsx`**

```tsx
"use client";

import { useEffect, useState } from "react";
import { FileUpload } from "@/components/file-upload";
import { listDocuments, type DocumentInfo } from "@/lib/api";

export default function AdminUploadPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);

  const fetchDocs = () => {
    listDocuments().then(setDocuments).catch(console.error);
  };

  useEffect(fetchDocs, []);

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="mb-6">
        <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
          &larr; Back to search
        </a>
      </div>
      <h1 className="text-2xl font-bold mb-6">Document Upload</h1>

      <FileUpload onUploadComplete={fetchDocs} />

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">
          Ingested Documents ({documents.length})
        </h2>
        <div className="border rounded-lg divide-y">
          {documents.map((doc) => (
            <div key={doc.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{doc.title}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.doc_type.toUpperCase()} &middot; {doc.chunk_count} chunks &middot; {doc.category}
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {new Date(doc.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
          {documents.length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground text-center">
              No documents ingested yet. Upload some above.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add frontend/components/file-upload.tsx frontend/app/admin/
git commit -m "feat: add admin document upload portal with drag-and-drop"
```

---

## Phase 9: Integration & Demo Data

### Task 14: Curate demo documents

**Step 1: Create a script to download public PDFs for demo**

Create `scripts/download_demo_data.sh`:

```bash
#!/bin/bash
# Downloads publicly available PDFs for demo purposes
# These simulate the types of documents Deloitte employees search for

OUT="data/sample-docs"
mkdir -p "$OUT"

echo "Downloading demo documents..."

# Public consulting/business reports (short + long, with tables/charts)
# Add URLs to publicly available PDFs here as the team curates them
# Example:
# curl -sL "https://example.com/report.pdf" -o "$OUT/annual-report-2024.pdf"

echo "Place PDF files in $OUT/ directory"
echo "Then run: docker compose exec backend python -m app.scripts.ingest_all"
```

**Step 2: Create batch ingestion script**

Create `backend/app/scripts/ingest_all.py`:

```python
"""Batch ingest all PDFs in /data/sample-docs/"""
import asyncio
import os

from app.core.database import async_session
from app.services.ingestion import ingest_document


async def main():
    docs_dir = "/data/sample-docs"
    files = [f for f in os.listdir(docs_dir) if f.lower().endswith((".pdf", ".docx", ".pptx"))]
    print(f"Found {len(files)} documents to ingest")

    async with async_session() as db:
        for i, filename in enumerate(files):
            path = os.path.join(docs_dir, filename)
            print(f"[{i+1}/{len(files)}] Ingesting {filename}...")
            try:
                doc, chunks = await ingest_document(db, path)
                print(f"  -> {doc.title}: {chunks} chunks")
            except Exception as e:
                print(f"  -> ERROR: {e}")

    print("Done!")


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 3: Commit**

```bash
mkdir -p scripts backend/app/scripts
touch backend/app/scripts/__init__.py
git add scripts/download_demo_data.sh backend/app/scripts/
git commit -m "feat: add demo data download script and batch ingestion"
```

---

### Task 15: Final integration — wire everything together

**Step 1: Verify `backend/app/main.py` has all routers**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import health, auth, documents, search


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield


app = FastAPI(
    title="Deloitte AI Search Engine",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(auth.router, prefix="/api", tags=["auth"])
app.include_router(documents.router, prefix="/api", tags=["documents"])
app.include_router(search.router, prefix="/api", tags=["search"])
```

**Step 2: End-to-end test sequence**

```bash
# 1. Start everything
docker compose up -d

# 2. Check health
curl http://localhost:8000/api/health

# 3. Upload a PDF
curl -X POST http://localhost:8000/api/documents \
  -F "file=@data/sample-docs/test.pdf" \
  -F "category=report"

# 4. Search
curl -X POST http://localhost:8000/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "quarterly financial results"}'

# 5. Open frontend
# http://localhost:3000
```

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: complete MVP integration — search engine prototype"
```

---

## Summary of Phases

| Phase | Tasks | What's Built |
|-------|-------|-------------|
| 1. Infrastructure | 1-2 | Directory structure, Docker Compose, Dockerfiles |
| 2. Database | 3-4 | Schema, SQLAlchemy models, Pydantic schemas |
| 3. Backend API | 5-6 | FastAPI app, health endpoint, auth/JWT |
| 4. Embeddings | 7 | Colab notebook, embedding client |
| 5. Ingestion | 8 | Docling parsing, chunking, embedding storage |
| 6. Search | 9 | Hybrid search, RRF, Cohere reranking |
| 7. Frontend | 10-12 | Next.js, landing page, search results, filters |
| 8. Admin Portal | 13 | Upload UI with drag-and-drop, document list |
| 9. Integration | 14-15 | Demo data, batch ingestion, end-to-end wiring |
