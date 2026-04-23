export type FileType = 'pptx' | 'docx' | 'pdf';

export interface Document {
  id: string;
  name: string;
  fileType: FileType;
  editedAt: string; // ISO date string
  thumbnailUrl?: string;
  author?: string;
  snippet?: string;
}

export interface UserProfile {
  id: string;
  name: string;
  firstName: string;
  avatarUrl?: string;
  email: string;
  department?: string;
  title?: string;
}

export interface SearchFilters {
  types: FileType[];
  dateRange?: { start: string; end: string };
  authorized?: 'all' | 'authorized-only' | 'public-only';
}

export interface SearchRequest {
  query: string;
  filters: SearchFilters;
}

export interface SearchResponse {
  results: Document[];
  totalCount: number;
}
