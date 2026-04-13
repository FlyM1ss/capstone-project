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
    document_group TEXT,
    version INTEGER DEFAULT 1 CHECK (version >= 1),
    content_hash TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_document_group_version UNIQUE (document_group, version)
);

-- Document title embeddings (separate table for clean separation)
CREATE TABLE IF NOT EXISTS document_title_embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    document_id UUID NOT NULL UNIQUE REFERENCES documents(id) ON DELETE CASCADE,
    title_text TEXT NOT NULL,
    embedding vector(1024),
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
CREATE INDEX IF NOT EXISTS idx_documents_document_group ON documents(document_group);
CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);

-- HNSW index for title embedding similarity search
CREATE INDEX IF NOT EXISTS idx_title_embeddings_vector
    ON document_title_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 200);

-- Seed demo users
INSERT INTO users (email, name, hashed_password, role) VALUES
    ('admin@deloitte.com', 'Admin User', '$2b$12$cRTowAa9DpbmZLmsMhKR6OzgjLxtaMptJ96DjxxgeRL/cx.kE/PcK', 'admin'),
    ('manager@deloitte.com', 'Manager User', '$2b$12$cRTowAa9DpbmZLmsMhKR6OzgjLxtaMptJ96DjxxgeRL/cx.kE/PcK', 'manager'),
    ('analyst@deloitte.com', 'Analyst User', '$2b$12$cRTowAa9DpbmZLmsMhKR6OzgjLxtaMptJ96DjxxgeRL/cx.kE/PcK', 'analyst')
ON CONFLICT (email) DO NOTHING;
-- All demo passwords: "password123"

-- NOTE: ParadeDB BM25 index is created AFTER data is ingested
-- because it needs at least one row. See backend ingestion service.
