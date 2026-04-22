import { useEffect, useState, useTransition } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Document, FileType, SearchFilters, SearchRequest } from '@/types';
import { searchDocuments } from '@/api/search';
import { ApiError } from '@/api/client';
import { getCachedSearch, setCachedSearch } from '@/api/searchCache';
import { FILE_TYPES } from '@/constants/filters';
import SearchBar from '@/components/SearchBar/SearchBar';
import FilterControls from '@/components/FilterControls/FilterControls';
import ResultItem from '@/components/ResultItem/ResultItem';
import styles from './ResultsPage.module.scss';

function describeSearchError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.errorCode === 'embedding_service_unavailable') {
      return 'Search is temporarily unavailable — the embedding service is offline. Please try again in a moment.';
    }
    if (err.status === 503) {
      return err.detail ?? 'Search service is temporarily unavailable. Please try again shortly.';
    }
    if (err.status >= 500) {
      return err.detail ?? `Search failed with a server error (${err.status}).`;
    }
    return err.detail ?? `Search failed (${err.status}).`;
  }
  return 'Could not reach the search backend. Check that it is running.';
}

export default function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
  const typesParam = searchParams.get('types');
  const dateStart = searchParams.get('dateStart') ?? '';
  const dateEnd = searchParams.get('dateEnd') ?? '';
  const authorizedParam = (searchParams.get('authorized') ?? 'all') as NonNullable<SearchFilters['authorized']>;

  const activeTypes: FileType[] = typesParam
    ? (typesParam.split(',') as FileType[])
    : FILE_TYPES;

  const filters: SearchFilters = {
    types: activeTypes,
    dateRange: dateStart || dateEnd ? { start: dateStart, end: dateEnd } : undefined,
    authorized: authorizedParam,
  };

  const request: SearchRequest = { query, filters };

  const [results, setResults] = useState<Document[]>(() =>
    query ? getCachedSearch(request)?.results ?? [] : []
  );
  const [totalCount, setTotalCount] = useState(() =>
    query ? getCachedSearch(request)?.totalCount ?? 0 : 0
  );
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    if (!query) return;
    const cached = getCachedSearch(request);
    if (cached) {
      setResults(cached.results);
      setTotalCount(cached.totalCount);
      setError(null);
      return;
    }
    startTransition(async () => {
      try {
        const res = await searchDocuments(request);
        setResults(res.results);
        setTotalCount(res.totalCount);
        setError(null);
        setCachedSearch(request, res);
      } catch (err) {
        console.error('Search failed:', err);
        setError(describeSearchError(err));
        setResults([]);
        setTotalCount(0);
      }
    });
  }, [query, typesParam, dateStart, dateEnd, authorizedParam]); // eslint-disable-line react-hooks/exhaustive-deps

  function updateParams(updates: Record<string, string | null>) {
    const params = new URLSearchParams(searchParams);
    for (const [key, val] of Object.entries(updates)) {
      if (val === null) params.delete(key);
      else params.set(key, val);
    }
    setSearchParams(params);
  }

  function toggleType(type: FileType) {
    const next = activeTypes.includes(type)
      ? activeTypes.filter((t) => t !== type)
      : [...activeTypes, type];
    updateParams({ types: next.length === FILE_TYPES.length ? null : next.join(',') });
  }

  function setDateRange(start: string, end: string) {
    updateParams({
      dateStart: start || null,
      dateEnd: end || null,
    });
  }

  function setAuthorized(val: NonNullable<SearchFilters['authorized']>) {
    updateParams({ authorized: val === 'all' ? null : val });
  }

  return (
    <div className={styles.page}>
      <div className={styles.searchArea}>
        <SearchBar initialQuery={query} onSearch={(q) => updateParams({ q })} />
        <div className={styles.filterRow}>
          <FilterControls
            filters={filters}
            onToggleType={toggleType}
            onSetDateRange={setDateRange}
            onSetAuthorized={setAuthorized}
          />
        </div>
      </div>

      <div className={styles.resultsArea}>
        {isPending ? (
          <div className={styles.loading}>
            <div className={styles.spinner} />
            <span>Searching...</span>
          </div>
        ) : error ? (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>Connection Error</p>
            <p className={styles.emptyText}>{error}</p>
          </div>
        ) : results.length > 0 ? (
          <>
            <p className={styles.resultCount}>
              {totalCount} result{totalCount !== 1 ? 's' : ''} for &ldquo;{query}&rdquo;
            </p>
            <div className={styles.resultsList}>
              {results.map((doc) => (
                <ResultItem key={doc.id} document={doc} />
              ))}
            </div>
          </>
        ) : query ? (
          <div className={styles.empty}>
            <p className={styles.emptyTitle}>No results found</p>
            <p className={styles.emptyText}>
              Try adjusting your search or filters for &ldquo;{query}&rdquo;
            </p>
          </div>
        ) : null}
      </div>
    </div>
  );
}
