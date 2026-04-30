import { SearchRequest, SearchResponse } from '@/types';

const CACHE_MAX = 20;
const cache = new Map<string, SearchResponse>();

function keyFor(req: SearchRequest): string {
  return JSON.stringify({
    q: req.query,
    t: [...req.filters.types].sort(),
    d: req.filters.dateRange ?? null,
    a: req.filters.authorized ?? 'all',
    v: req.filters.version ?? 'latest-only',
  });
}

export function getCachedSearch(req: SearchRequest): SearchResponse | undefined {
  return cache.get(keyFor(req));
}

export function setCachedSearch(req: SearchRequest, res: SearchResponse): void {
  const k = keyFor(req);
  if (cache.has(k)) cache.delete(k);
  cache.set(k, res);
  if (cache.size > CACHE_MAX) {
    const oldest = cache.keys().next().value;
    if (oldest !== undefined) cache.delete(oldest);
  }
}

export function clearSearchCache(): void {
  cache.clear();
}
