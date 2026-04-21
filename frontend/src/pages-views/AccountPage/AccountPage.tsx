import { useUser } from '@/context/UserContext';
import { getInitials } from '@/utils/getInitials';
import styles from './AccountPage.module.scss';

export default function AccountPage() {
  const user = useUser();
  const initials = getInitials(user);

  return (
    <div className={styles.page}>
      <h1 className={styles.pageTitle}>Account</h1>

      {/* Profile card */}
      <div className={styles.card}>
        <div className={styles.profileHeader}>
          <div className={styles.avatarLarge}>
            {user?.avatarUrl ? (
              <img src={user.avatarUrl} alt={user.name} className={styles.avatarImg} />
            ) : (
              <span className={styles.avatarInitials}>{initials}</span>
            )}
          </div>
          <div className={styles.profileInfo}>
            <h2 className={styles.name}>{user?.name ?? '—'}</h2>
            {user?.title && <p className={styles.title}>{user.title}</p>}
            {user?.department && (
              <p className={styles.department}>{user.department}</p>
            )}
          </div>
        </div>
        <div className={styles.divider} />
        <div className={styles.fields}>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Email</span>
            <span className={styles.fieldValue}>{user?.email ?? '—'}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Department</span>
            <span className={styles.fieldValue}>{user?.department ?? '—'}</span>
          </div>
          <div className={styles.field}>
            <span className={styles.fieldLabel}>Role</span>
            <span className={styles.fieldValue}>{user?.title ?? '—'}</span>
          </div>
        </div>
      </div>

      {/* Display preferences */}
      <div className={styles.card}>
        <h3 className={styles.sectionTitle}>Display Preferences</h3>
        <div className={styles.preferenceList}>
          <div className={styles.preference}>
            <div>
              <p className={styles.prefLabel}>Compact sidebar</p>
              <p className={styles.prefDescription}>Show fewer documents in the sidebar at once</p>
            </div>
            <button className={styles.toggle} aria-label="Toggle compact sidebar" disabled>
              <span className={styles.toggleKnob} />
            </button>
          </div>
          <div className={styles.preference}>
            <div>
              <p className={styles.prefLabel}>Show snippets in results</p>
              <p className={styles.prefDescription}>Display document previews below search results</p>
            </div>
            <button className={`${styles.toggle} ${styles.toggleOn}`} aria-label="Toggle snippets" disabled>
              <span className={styles.toggleKnob} />
            </button>
          </div>
        </div>
      </div>

      {/* Notification settings */}
      <div className={styles.card}>
        <h3 className={styles.sectionTitle}>Notification Settings</h3>
        <div className={styles.preferenceList}>
          <div className={styles.preference}>
            <div>
              <p className={styles.prefLabel}>Email digest</p>
              <p className={styles.prefDescription}>Receive a weekly summary of recent documents</p>
            </div>
            <button className={styles.toggle} aria-label="Toggle email digest" disabled>
              <span className={styles.toggleKnob} />
            </button>
          </div>
          <div className={styles.preference}>
            <div>
              <p className={styles.prefLabel}>Pinned document alerts</p>
              <p className={styles.prefDescription}>Get notified when pinned documents are updated</p>
            </div>
            <button className={`${styles.toggle} ${styles.toggleOn}`} aria-label="Toggle pinned alerts" disabled>
              <span className={styles.toggleKnob} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
