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
  version: number | null;
  document_group: string | null;
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
  token?: string | null,
  showLatestOnly: boolean = true,
): Promise<SearchResponse> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/api/search`, {
    method: "POST",
    headers,
    body: JSON.stringify({ query, filters, show_latest_only: showLatestOnly }),
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

export async function uploadDocument(formData: FormData, token?: string | null): Promise<void> {
  const headers: Record<string, string> = {};
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${API_URL}/api/documents`, {
    method: "POST",
    headers,
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Upload failed");
  }
}
