import { FileType } from '@/types';
import styles from './FileTypeBadge.module.scss';

interface Props {
  fileType: FileType;
}

export default function FileTypeBadge({ fileType }: Props) {
  return (
    <span className={`${styles.badge} ${styles[fileType]}`}>
      .{fileType}
    </span>
  );
}
