import { Document } from '@/types';
import { apiGet } from './client';
import { mockPinnedDocuments, mockRecentDocuments } from '@/data/mockData';

export async function getPinnedDocuments(): Promise<Document[]> {
  return apiGet<Document[]>('/documents/pinned', mockPinnedDocuments);
}

export async function getRecentDocuments(): Promise<Document[]> {
  return apiGet<Document[]>('/documents/recent', mockRecentDocuments);
}
