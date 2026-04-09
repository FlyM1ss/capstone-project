import { useRef, useState, ReactNode } from 'react';
import { useClickOutside } from '@/hooks/useClickOutside';
import styles from './FilterChip.module.scss';

interface Props {
  label: string;
  icon?: ReactNode;
  isActive?: boolean;
  children: ReactNode; // dropdown content
}

export default function FilterChip({ label, icon, isActive, children }: Props) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useClickOutside(ref, () => setOpen(false));

  return (
    <div className={styles.wrapper} ref={ref}>
      <button
        className={`${styles.chip} ${isActive ? styles.active : ''} ${open ? styles.open : ''}`}
        onClick={() => setOpen((v) => !v)}
        type="button"
      >
        {icon && <span className={styles.icon}>{icon}</span>}
        <span className={styles.label}>{label}</span>
        <svg className={`${styles.caret} ${open ? styles.caretOpen : ''}`} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      {open && (
        <div className={styles.dropdown}>
          {children}
        </div>
      )}
    </div>
  );
}
