import { Document, FileType } from '@/types';
import { apiGet, BASE_URL } from './client';

// Backend response type (matches backend DocumentOut schema)
interface BackendDocument {
  id: string;
  title: string;
  author: string | null;
  doc_type: string;
  category: string;
  access_level: string;
  file_path: string | null;
  page_count: number | null;
  chunk_count: number;
  created_at: string;
}

function normalizeFileType(docType: string): FileType {
  const lower = docType.toLowerCase();
  if (lower.includes('pdf')) return 'pdf';
  if (lower.includes('docx') || lower.includes('word')) return 'docx';
  if (lower.includes('pptx') || lower.includes('powerpoint') || lower.includes('ppt')) return 'pptx';
  return 'pdf';
}

function toDocument(item: BackendDocument): Document {
  return {
    id: item.id,
    name: item.title,
    fileType: normalizeFileType(item.doc_type),
    editedAt: item.created_at,
    isPinned: false,
    author: item.author ?? undefined,
  };
}

// Pure API fetch — pin/recent state is managed by DocumentsContext, not here.
export async function getDocuments(): Promise<Document[]> {
  const raw = await apiGet<BackendDocument[]>('/api/documents');
  return raw.map(toDocument);
}

export type { BackendDocument as DocumentDetail };

export async function getDocumentById(id: string): Promise<BackendDocument> {
  return apiGet<BackendDocument>(`/api/documents/${id}`);
}

export interface DocumentChunk {
  chunk_index: number;
  content: string;
}

export async function getDocumentChunks(id: string): Promise<DocumentChunk[]> {
  const res = await apiGet<{ document_id: string; chunks: DocumentChunk[] }>(
    `/api/documents/${id}/chunks`,
  );
  return res.chunks;
}

export function getDocumentFileUrl(id: string): string {
  return `${BASE_URL}/api/documents/${id}/file`;
}

export function getDocumentPreviewUrl(id: string): string {
  return `${BASE_URL}/api/documents/${id}/preview`;
}

export interface DocumentSummary {
  document_id: string;
  summary: string | null;
  cached: boolean;
  generated_at: string | null;
}

export async function getDocumentSummary(id: string): Promise<DocumentSummary> {
  return apiGet<DocumentSummary>(`/api/documents/${id}/summary`);
}
