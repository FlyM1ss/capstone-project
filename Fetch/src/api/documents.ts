import { Document, FileType } from '@/types';
import { apiGet } from './client';

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

// Pinned state stored client-side in localStorage
function getPinnedIds(): Set<string> {
  try {
    const raw = localStorage.getItem('fetch-pinned-docs');
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

export function togglePinDocument(docId: string): void {
  const pinned = getPinnedIds();
  if (pinned.has(docId)) {
    pinned.delete(docId);
  } else {
    pinned.add(docId);
  }
  localStorage.setItem('fetch-pinned-docs', JSON.stringify([...pinned]));
}

export async function getDocuments(): Promise<{ pinned: Document[]; recent: Document[] }> {
  const raw = await apiGet<BackendDocument[]>('/api/documents');
  const pinnedIds = getPinnedIds();

  const allDocs = raw.map(toDocument).map((doc) => ({
    ...doc,
    isPinned: pinnedIds.has(doc.id),
  }));

  return {
    pinned: allDocs.filter((d) => d.isPinned),
    recent: allDocs.filter((d) => !d.isPinned).slice(0, 10),
  };
}
