import { FileType, SearchFilters } from '@/types';

export const FILE_TYPES: FileType[] = ['pptx', 'pdf', 'docx'];

export const AUTHORIZED_OPTIONS: { value: NonNullable<SearchFilters['authorized']>; label: string }[] = [
  { value: 'all', label: 'All documents' },
  { value: 'authorized-only', label: 'Authorized only' },
  { value: 'public-only', label: 'Public only' },
];

export const VERSION_OPTIONS: { value: NonNullable<SearchFilters['version']>; label: string }[] = [
  { value: 'latest-only', label: 'Latest version only' },
  { value: 'all-versions', label: 'All versions' },
  { value: 'oldest-only', label: 'Oldest version only' },
];
