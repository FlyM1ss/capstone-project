import { ChangeEvent, FormEvent, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SearchFilters } from '@/types';
import { getQueryBlockReason } from '@/utils/queryValidation';
import styles from './SearchBar.module.scss';

interface Props {
  initialQuery?: string;
  filters?: SearchFilters;
  onSearch?: (query: string) => void;
  warning?: string | null;
}

export default function SearchBar({ initialQuery = '', filters, onSearch, warning }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const [localWarning, setLocalWarning] = useState<string | null>(null);
  const [suppressed, setSuppressed] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    setSuppressed(false);
  }, [warning]);

  const displayWarning = suppressed ? null : localWarning ?? warning ?? null;

  function handleChange(e: ChangeEvent<HTMLInputElement>) {
    setQuery(e.target.value);
    if (localWarning) setLocalWarning(null);
    if (!suppressed) setSuppressed(true);
  }

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const trimmed = query.trim();
    if (!trimmed) return;

    setSuppressed(false);
    const blockReason = getQueryBlockReason(trimmed);
    if (blockReason) {
      setLocalWarning(blockReason);
      return;
    }
    setLocalWarning(null);

    if (onSearch) {
      onSearch(trimmed);
      return;
    }

    const params = new URLSearchParams();
    params.set('q', trimmed);
    if (filters?.types?.length) params.set('types', filters.types.join(','));
    if (filters?.dateRange?.start) params.set('dateStart', filters.dateRange.start);
    if (filters?.dateRange?.end) params.set('dateEnd', filters.dateRange.end);
    if (filters?.authorized) params.set('authorized', filters.authorized);
    if (filters?.version) params.set('version', filters.version);

    navigate(`/results?${params.toString()}`);
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} role="search">
      <div className={styles.wrapper}>
        <input
          className={styles.input}
          type="text"
          value={query}
          onChange={handleChange}
          placeholder="Search for decks, documents, policies..."
          aria-label="Search"
          aria-invalid={displayWarning ? true : undefined}
          aria-describedby={displayWarning ? 'search-bar-warning' : undefined}
        />
        <button className={styles.button} type="submit" aria-label="Search">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>
      </div>
      {displayWarning && (
        <div
          id="search-bar-warning"
          className={styles.warning}
          role="status"
          aria-live="polite"
        >
          {displayWarning}
        </div>
      )}
    </form>
  );
}
