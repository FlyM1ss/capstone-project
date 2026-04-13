import { Document, FileType, SearchFilters, SearchRequest, SearchResponse } from '@/types';
import { apiPost } from './client';
import { mockSearchResults } from '@/data/mockData';

// Backend response types (snake_case from FastAPI)
interface BackendSearchResultItem {
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
  version: number | null;
  document_group: string | null;
}

interface BackendSearchResponse {
  query: string;
  results: BackendSearchResultItem[];
  total: number;
  latency_ms: number;
}

function normalizeFileType(docType: string): FileType {
  const lower = docType.toLowerCase();
  if (lower.includes('pdf')) return 'pdf';
  if (lower.includes('docx') || lower.includes('word')) return 'docx';
  if (lower.includes('pptx') || lower.includes('powerpoint') || lower.includes('ppt')) return 'pptx';
  return 'pdf';
}

function toDocument(item: BackendSearchResultItem): Document {
  return {
    id: item.document_id,
    name: item.title,
    fileType: normalizeFileType(item.doc_type),
    editedAt: item.created_date ?? new Date().toISOString(),
    isPinned: false,
    author: item.author ?? undefined,
    snippet: item.snippet,
  };
}

function buildBackendFilters(filters: SearchFilters): Record<string, string> | undefined {
  const out: Record<string, string> = {};

  if (filters.authorized === 'public-only') {
    out.access_level = 'public';
  } else if (filters.authorized === 'authorized-only') {
    out.access_level = 'internal';
  }

  return Object.keys(out).length ? out : undefined;
}

export async function searchDocuments(req: SearchRequest): Promise<SearchResponse> {
  const backendReq = {
    query: req.query,
    filters: buildBackendFilters(req.filters),
    show_latest_only: true,
  };

  const raw = await apiPost<BackendSearchResponse | null>(
    '/api/search',
    backendReq,
    null
  );

  if (!raw) {
    return mockSearchResults;
  }

  return {
    results: raw.results.map(toDocument),
    totalCount: raw.total,
  };
}
