import { FormEvent, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SearchFilters } from '@/types';
import styles from './SearchBar.module.scss';

interface Props {
  initialQuery?: string;
  externalQuery?: string;
  filters?: SearchFilters;
  onSearch?: (query: string) => void;
}

export default function SearchBar({ initialQuery = '', externalQuery, filters, onSearch }: Props) {
  const [query, setQuery] = useState(initialQuery);
  const navigate = useNavigate();

  useEffect(() => {
    if (externalQuery !== undefined) setQuery(externalQuery);
  }, [externalQuery]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    if (onSearch) {
      onSearch(query.trim());
      return;
    }

    const params = new URLSearchParams();
    params.set('q', query.trim());
    if (filters?.types?.length) params.set('types', filters.types.join(','));
    if (filters?.dateRange?.start) params.set('dateStart', filters.dateRange.start);
    if (filters?.dateRange?.end) params.set('dateEnd', filters.dateRange.end);
    if (filters?.authorized) params.set('authorized', filters.authorized);

    navigate(`/results?${params.toString()}`);
  }

  return (
    <form className={styles.form} onSubmit={handleSubmit} role="search">
      <div className={styles.wrapper}>
        <input
          className={styles.input}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search for decks, documents, policies..."
          aria-label="Search"
        />
        <button className={styles.button} type="submit" aria-label="Search">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        </button>
      </div>
    </form>
  );
}
