import { useDocuments } from '@/context/DocumentsContext';
import DocumentCard from '@/components/DocumentCard/DocumentCard';
import styles from './Sidebar.module.scss';

interface Props {
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({ isOpen, onToggle }: Props) {
  const { pinned, recents, isPinned } = useDocuments();
  const recentsUnpinned = recents.filter((d) => !isPinned(d.id));

  return (
    <aside className={`${styles.sidebar} ${!isOpen ? styles.collapsed : ''}`}>
      <div className={styles.toggleRow}>
        <button
          type="button"
          className={styles.toggleBtn}
          onClick={onToggle}
          aria-expanded={isOpen}
          aria-controls="sidebar-panel"
          aria-label={isOpen ? 'Collapse sidebar' : 'Expand sidebar'}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        </button>
      </div>

      <div id="sidebar-panel" className={styles.inner}>
        <div className={styles.content}>
          {/* Pinned section */}
          {pinned.length > 0 && (
            <section className={styles.section}>
              <div className={styles.sectionHeader}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <line x1="12" y1="17" x2="12" y2="22" />
                  <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 10.76V6h1a2 2 0 0 0 0-4H8a2 2 0 0 0 0 4h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.9A2 2 0 0 0 5 15.24Z" />
                </svg>
                <span>Pinned</span>
              </div>
              {pinned.map((doc) => (
                <DocumentCard key={doc.id} document={doc} />
              ))}
            </section>
          )}

          {/* Recents section */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <span>Recents</span>
            </div>
            {recentsUnpinned.length > 0 ? (
              recentsUnpinned.map((doc) => (
                <DocumentCard key={doc.id} document={doc} />
              ))
            ) : (
              <p className={styles.sectionHeader} style={{ opacity: 0.5, fontSize: '0.8rem' }}>
                No documents yet
              </p>
            )}
          </section>
        </div>
      </div>
    </aside>
  );
}
