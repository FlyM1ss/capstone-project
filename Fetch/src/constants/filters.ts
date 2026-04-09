import { FileType, SearchFilters } from '@/types';

export const FILE_TYPES: FileType[] = ['pptx', 'pdf', 'docx'];

export const AUTHORIZED_OPTIONS: { value: NonNullable<SearchFilters['authorized']>; label: string }[] = [
  { value: 'all', label: 'All documents' },
  { value: 'authorized-only', label: 'Authorized only' },
  { value: 'public-only', label: 'Public only' },
];
