import { useEffect, useState, useTransition } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Document, FileType, SearchFilters } from '@/types';
import { searchDocuments } from '@/api/search';
import { FILE_TYPES } from '@/constants/filters';
import SearchBar from '@/components/SearchBar/SearchBar';
import FilterControls from '@/components/FilterControls/FilterControls';
import ResultItem from '@/components/ResultItem/ResultItem';
import styles from './ResultsPage.module.scss';

export default function ResultsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const query = searchParams.get('q') ?? '';
  const typesParam = searchParams.get('types');
  const dateStart = searchParams.get('dateStart') ?? '';
  const dateEnd = searchParams.get('dateEnd') ?? '';
  const authorizedParam = (searchParams.get('authorized') ?? 'all') as NonNullable<SearchFilters['authorized']>;

  const [results, setResults] = useState<Document[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  const activeTypes: FileType[] = typesParam
    ? (typesParam.split(',') as FileType[])
    : FILE_TYPES;

  const filters: SearchFilters = {
    types: activeTypes,
    dateRange: dateStart || dateEnd ? { start: dateStart, end: dateEnd } : undefined,
    authorized: authorizedParam,
  };

  useEffect(() => {
    if (!query) return;
    startTransition(async () => {
      try {
        const res = await searchDocuments({ query, filters });
        setResults(res.results);
        setTotalCount(res.totalCount);
        setError(null);
      } catch (err) {
        console.error('Search failed:', err);
        setError('Search failed. Make sure the backend is running.');
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
    updateParams({ types: next.join(',') });
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
