import { Document, FileType, SearchFilters, SearchRequest, SearchResponse } from '@/types';
import { apiPost } from './client';

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

  // Access level filter
  if (filters.authorized === 'public-only') {
    out.access_level = 'public';
  } else if (filters.authorized === 'authorized-only') {
    out.access_level = 'internal';
  }

  // File type filter: only send if not all types are selected
  const allTypes: FileType[] = ['pptx', 'pdf', 'docx'];
  if (filters.types.length > 0 && filters.types.length < allTypes.length) {
    out.doc_type = filters.types.join(',');
  }

  return Object.keys(out).length ? out : undefined;
}

export async function searchDocuments(req: SearchRequest): Promise<SearchResponse> {
  const backendReq = {
    query: req.query,
    filters: buildBackendFilters(req.filters),
    show_latest_only: true,
  };

  const raw = await apiPost<BackendSearchResponse>('/api/search', backendReq);

  // Client-side date range filtering (backend doesn't support date range filter natively)
  let results = raw.results.map(toDocument);

  if (req.filters.dateRange?.start || req.filters.dateRange?.end) {
    const start = req.filters.dateRange.start ? new Date(req.filters.dateRange.start) : null;
    const end = req.filters.dateRange.end ? new Date(req.filters.dateRange.end) : null;
    results = results.filter((doc) => {
      const docDate = new Date(doc.editedAt);
      if (start && docDate < start) return false;
      if (end && docDate > end) return false;
      return true;
    });
  }

  return {
    results,
    totalCount: results.length,
  };
}
