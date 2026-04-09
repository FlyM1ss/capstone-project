import { Link } from 'react-router-dom';
import { useUser } from '@/context/UserContext';
import { getInitials } from '@/utils/getInitials';
import styles from './Header.module.scss';

export default function Header() {
  const user = useUser();

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <Link to="/" className={styles.logo} aria-label="Fetch home">
          <img src="/logo.svg" alt="Fetch" className={styles.logoImg} />
        </Link>
      </div>
      <div className={styles.right}>
        <Link to="/account" className={styles.avatar} aria-label="Account">
          {user?.avatarUrl ? (
            <img src={user.avatarUrl} alt={user.name} className={styles.avatarImg} />
          ) : (
            <span className={styles.avatarInitials}>{getInitials(user)}</span>
          )}
        </Link>
      </div>
    </header>
  );
}
