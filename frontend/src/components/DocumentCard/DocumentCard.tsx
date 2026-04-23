import { Link } from 'react-router-dom';
import { Document } from '@/types';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import { timeAgo } from '@/utils/timeAgo';
import { useDocuments } from '@/context/DocumentsContext';
import styles from './DocumentCard.module.scss';

interface Props {
  document: Document;
}

export default function DocumentCard({ document }: Props) {
  const { togglePin, recordVisit, isPinned } = useDocuments();
  const pinned = isPinned(document.id);

  const handlePin = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    togglePin(document);
  };

  return (
    <Link to={`/document/${document.id}`} className={styles.card} onClick={() => recordVisit(document)}>
      <div className={styles.info}>
        <span className={styles.name}>{document.name}</span>
        <span className={styles.meta}>edited {timeAgo(document.editedAt)}</span>
        <FileTypeBadge fileType={document.fileType} />
      </div>
      <button
        type="button"
        className={`${styles.pin} ${pinned ? styles.pinActive : ''}`}
        onClick={handlePin}
        aria-label={pinned ? 'Unpin document' : 'Pin document'}
      >
        <svg width="12" height="12" viewBox="0 0 24 24" fill={pinned ? 'currentColor' : 'none'} stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <line x1="12" y1="17" x2="12" y2="22" />
          <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
        </svg>
      </button>
    </Link>
  );
}
