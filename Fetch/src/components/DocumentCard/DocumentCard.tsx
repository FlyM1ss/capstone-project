import { Link } from 'react-router-dom';
import { Document } from '@/types';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import { timeAgo } from '@/utils/timeAgo';
import styles from './DocumentCard.module.scss';

interface Props {
  document: Document;
}

export default function DocumentCard({ document }: Props) {
  return (
    <Link to={`/document/${document.id}`} className={styles.card}>
      <div className={styles.thumbnail} aria-hidden="true" />
      <div className={styles.info}>
        <span className={styles.name}>{document.name}</span>
        <span className={styles.meta}>edited {timeAgo(document.editedAt)}</span>
        <FileTypeBadge fileType={document.fileType} />
      </div>
    </Link>
  );
}
