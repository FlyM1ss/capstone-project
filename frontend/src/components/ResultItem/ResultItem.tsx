import { Link } from 'react-router-dom';
import { Document } from '@/types';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import { timeAgo } from '@/utils/timeAgo';
import { useDocuments } from '@/context/DocumentsContext';
import { useDocumentSummary } from '@/context/SummaryCacheContext';
import styles from './ResultItem.module.scss';

interface Props {
  document: Document;
  isSummaryOpen?: boolean;
  onToggleSummary?: (doc: Document) => void;
}

// Label is a pure function of (panel open?, cache entry status).
// - never fetched + closed  → "Summarize"
// - fetching + open         → "Generating"
// - fetching + closed       → "See Summary" (keeps running in background)
// - loaded + open           → "Summarized"
// - loaded + closed         → "See Summary"
// - error + open            → "Summarize" (inviting retry)
// - error + closed          → "Summarize"
function summarizeLabel(
  isOpen: boolean,
  status: 'idle' | 'loading' | 'loaded' | 'error',
): string {
  if (isOpen) {
    if (status === 'loaded') return 'Summarized';
    if (status === 'loading') return 'Generating';
    return 'Summarize';
  }
  if (status === 'loaded' || status === 'loading') return 'See Summary';
  return 'Summarize';
}

export default function ResultItem({ document, isSummaryOpen, onToggleSummary }: Props) {
  const { recordVisit, togglePin } = useDocuments();
  const entry = useDocumentSummary(document.id);
  const status: 'idle' | 'loading' | 'loaded' | 'error' = entry?.status ?? 'idle';

  const handlePin = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    togglePin(document);
  };

  const handleSummarize = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    onToggleSummary?.(document);
  };

  const open = !!isSummaryOpen;
  const label = summarizeLabel(open, status);
  const isBusy = open && status === 'loading';

  return (
    <Link to={`/document/${document.id}`} className={styles.item} onClick={() => recordVisit(document)}>
      <div className={styles.header}>
        <h3 className={styles.title}>{document.name}</h3>
        <div className={styles.headerActions}>
          {onToggleSummary && (
            <button
              type="button"
              className={`${styles.summarize} ${open ? styles.summarizeActive : ''}`}
              onClick={handleSummarize}
              aria-pressed={open}
            >
              {isBusy && <span className={styles.summarizeSpinner} aria-hidden="true" />}
              <span>{label}</span>
            </button>
          )}
          <FileTypeBadge fileType={document.fileType} />
          <button
            type="button"
            className={`${styles.pin} ${document.isPinned ? styles.pinActive : ''}`}
            onClick={handlePin}
            aria-label={document.isPinned ? 'Unpin document' : 'Pin document'}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill={document.isPinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <line x1="12" y1="17" x2="12" y2="22" />
              <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
            </svg>
          </button>
        </div>
      </div>
      {document.snippet && (
        <p className={styles.snippet}>{document.snippet}</p>
      )}
      <div className={styles.meta}>
        {document.author && <span>{document.author}</span>}
        <span>·</span>
        <span>edited {timeAgo(document.editedAt)}</span>
      </div>
    </Link>
  );
}
