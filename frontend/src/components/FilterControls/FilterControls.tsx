import { FileType, SearchFilters } from '@/types';
import FilterChip from '@/components/FilterChip/FilterChip';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import { FILE_TYPES, AUTHORIZED_OPTIONS } from '@/constants/filters';
import styles from './FilterControls.module.scss';

interface Props {
  filters: SearchFilters;
  onToggleType: (type: FileType) => void;
  onSetDateRange: (start: string, end: string) => void;
  onSetAuthorized: (val: NonNullable<SearchFilters['authorized']>) => void;
}

const FileIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
    <polyline points="14 2 14 8 20 8" />
  </svg>
);

const CalendarIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="18" rx="2" ry="2" />
    <line x1="16" y1="2" x2="16" y2="6" />
    <line x1="8" y1="2" x2="8" y2="6" />
    <line x1="3" y1="10" x2="21" y2="10" />
  </svg>
);

const LockIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
    <path d="M7 11V7a5 5 0 0 1 10 0v4" />
  </svg>
);

export default function FilterControls({ filters, onToggleType, onSetDateRange, onSetAuthorized }: Props) {
  const dateStart = filters.dateRange?.start ?? '';
  const dateEnd = filters.dateRange?.end ?? '';

  return (
    <>
      <FilterChip
        label="type"
        isActive={filters.types.length < FILE_TYPES.length}
        icon={<FileIcon />}
      >
        <div className={styles.section}>
          <p className={styles.label}>File type</p>
          {FILE_TYPES.map((type) => (
            <label key={type} className={styles.checkOption}>
              <input
                type="checkbox"
                checked={filters.types.includes(type)}
                onChange={() => onToggleType(type)}
              />
              <FileTypeBadge fileType={type} />
            </label>
          ))}
        </div>
      </FilterChip>

      <FilterChip
        label="Range"
        isActive={!!(dateStart || dateEnd)}
        icon={<CalendarIcon />}
      >
        <div className={styles.section}>
          <p className={styles.label}>Date range</p>
          <label className={styles.dateLabel}>
            From
            <input
              type="date"
              className={styles.dateInput}
              value={dateStart}
              onChange={(e) => onSetDateRange(e.target.value, dateEnd)}
            />
          </label>
          <label className={styles.dateLabel}>
            To
            <input
              type="date"
              className={styles.dateInput}
              value={dateEnd}
              onChange={(e) => onSetDateRange(dateStart, e.target.value)}
            />
          </label>
        </div>
      </FilterChip>

      <FilterChip
        label="Authorized"
        isActive={filters.authorized !== 'all'}
        icon={<LockIcon />}
      >
        <div className={styles.section}>
          <p className={styles.label}>Access level</p>
          {AUTHORIZED_OPTIONS.map((opt) => (
            <label key={opt.value} className={styles.radioOption}>
              <input
                type="radio"
                name="authorized-filter"
                value={opt.value}
                checked={filters.authorized === opt.value}
                onChange={() => onSetAuthorized(opt.value)}
              />
              <span>{opt.label}</span>
            </label>
          ))}
        </div>
      </FilterChip>
    </>
  );
}
