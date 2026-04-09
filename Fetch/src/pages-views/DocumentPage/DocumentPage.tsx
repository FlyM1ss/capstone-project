import { useParams } from 'react-router-dom';
import styles from './DocumentPage.module.scss';

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();

  return (
    <div className={styles.page}>
      <p className={styles.placeholder}>Document preview — id: {id}</p>
    </div>
  );
}
