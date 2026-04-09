import { useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useUser } from '@/context/UserContext';
import { useTheme } from '@/context/ThemeContext';
import { getInitials } from '@/utils/getInitials';
import styles from './Header.module.scss';

function SunIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="5" />
      <line x1="12" y1="1" x2="12" y2="3" />
      <line x1="12" y1="21" x2="12" y2="23" />
      <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
      <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
      <line x1="1" y1="12" x2="3" y2="12" />
      <line x1="21" y1="12" x2="23" y2="12" />
      <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
      <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
    </svg>
  );
}

function MoonIcon() {
  return (
    <svg
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
    </svg>
  );
}

export default function Header() {
  const user = useUser();
  const { theme, toggleTheme } = useTheme();
  const [animating, setAnimating] = useState(false);
  const [sweeping, setSweeping] = useState(false);

  const handleToggle = useCallback(() => {
    if (sweeping) return;
    setSweeping(true);
    setAnimating(true);
    toggleTheme();
  }, [sweeping, toggleTheme]);

  const handleSweepEnd = useCallback(() => {
    setSweeping(false);
  }, []);

  // Clear icon animation state
  useEffect(() => {
    if (!animating) return;
    const timer = setTimeout(() => setAnimating(false), 500);
    return () => clearTimeout(timer);
  }, [animating]);

  return (
    <>
      {sweeping && (
        <div
          className={`${styles.sweepOverlay} ${
            theme === 'dark' ? styles.sweepDark : styles.sweepLight
          }`}
          onAnimationEnd={handleSweepEnd}
        />
      )}
      <header className={styles.header}>
        <div className={styles.left}>
          <Link to="/" className={styles.logo} aria-label="Fetch home">
            <img src="/logo.svg" alt="Fetch" className={styles.logoImg} />
          </Link>
        </div>
        <div className={styles.right}>
          <button
            className={styles.themeToggle}
            onClick={handleToggle}
            aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            <span className={`${styles.iconWrap} ${animating ? styles.animating : ''}`}>
              {theme === 'dark' ? <MoonIcon /> : <SunIcon />}
            </span>
          </button>
          <Link to="/account" className={styles.avatar} aria-label="Account">
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className={styles.avatarImg} />
            ) : (
              <span className={styles.avatarInitials}>{getInitials(user)}</span>
            )}
          </Link>
        </div>
      </header>
    </>
  );
}
