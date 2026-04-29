import { useState } from 'react';
import { FileType, SearchFilters } from '@/types';
import { useUser } from '@/context/UserContext';
import Greeting from '@/components/Greeting/Greeting';
import SearchBar from '@/components/SearchBar/SearchBar';
import FilterControls from '@/components/FilterControls/FilterControls';
import styles from './SearchPage.module.scss';

export default function SearchPage() {
  const user = useUser();
  const [filters, setFilters] = useState<SearchFilters>({
    types: ['pptx', 'pdf', 'docx'],
    authorized: 'all',
    version: 'latest-only',
  });

  function toggleType(type: FileType) {
    setFilters((prev) => ({
      ...prev,
      types: prev.types.includes(type)
        ? prev.types.filter((t) => t !== type)
        : [...prev.types, type],
    }));
  }

  function setDateRange(start: string, end: string) {
    setFilters((prev) => ({ ...prev, dateRange: { start, end } }));
  }

  function setAuthorized(val: NonNullable<SearchFilters['authorized']>) {
    setFilters((prev) => ({ ...prev, authorized: val }));
  }

  function setVersion(val: NonNullable<SearchFilters['version']>) {
    setFilters((prev) => ({ ...prev, version: val }));
  }

  return (
    <div className={styles.page}>
      <div className={styles.center}>
        <Greeting firstName={user?.firstName ?? 'there'} />

        <div className={styles.searchSection}>
          <SearchBar filters={filters} />

          <div className={styles.filterRow}>
            <FilterControls
              filters={filters}
              onToggleType={toggleType}
              onSetDateRange={setDateRange}
              onSetAuthorized={setAuthorized}
              onSetVersion={setVersion}
            />

            <button className={styles.voiceButton} type="button" aria-label="Voice search (coming soon)" disabled style={{ opacity: 0.4, cursor: 'not-allowed' }}>
              <svg width="18" height="18" viewBox="0 0 98 98" fill="none" stroke="currentColor" strokeWidth="13.3333" strokeLinecap="round" strokeLinejoin="round">
                <path d="M8.167 40.833V53.083M24.5 24.5V69.417M40.834 12.25V85.75M57.167 32.667V61.25M73.5 20.417V73.5M89.834 40.833V53.083" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
