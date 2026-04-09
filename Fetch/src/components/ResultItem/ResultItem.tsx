import { Link } from 'react-router-dom';
import { Document } from '@/types';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import { timeAgo } from '@/utils/timeAgo';
import styles from './ResultItem.module.scss';

interface Props {
  document: Document;
}

export default function ResultItem({ document }: Props) {
  return (
    <Link to={`/document/${document.id}`} className={styles.item}>
      <div className={styles.header}>
        <h3 className={styles.title}>{document.name}</h3>
        <FileTypeBadge fileType={document.fileType} />
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
