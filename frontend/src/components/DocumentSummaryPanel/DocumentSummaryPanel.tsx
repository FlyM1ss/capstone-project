import { useEffect, useState } from 'react';
import { ApiError } from '@/api/client';
import {
  useDocumentSummary,
  useSummaryCache,
} from '@/context/SummaryCacheContext';
import styles from './DocumentSummaryPanel.module.scss';

interface Props {
  documentId: string;
}

function parseBullets(raw: string): string[] {
  return raw
    .split('\n')
    .map((line) => line.replace(/^[-*•]\s+/, '').trim())
    .filter((line) => line.length > 0);
}

function getErrorMessage(err: unknown): string {
  if (!(err instanceof ApiError)) return 'Could not load summary.';
  if (err.body?.error_code === 'summarizer_unavailable') {
    return 'Summary service is unavailable right now.';
  }
  return err.detail ?? 'Could not load summary.';
}

const SLOW_CALL_THRESHOLD_MS = 6000;
const SKELETON_WIDTHS = [92, 78, 85, 70, 88];

export default function DocumentSummaryPanel({ documentId }: Props) {
  const cache = useSummaryCache();
  const entry = useDocumentSummary(documentId);
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    setSlow(false);
    cache.ensure(documentId).catch(() => {
      // error is captured in the cache entry; swallow to avoid an
      // unhandled-rejection warning when no UI caller awaits the Promise.
    });
    const t = window.setTimeout(() => setSlow(true), SLOW_CALL_THRESHOLD_MS);
    return () => window.clearTimeout(t);
  }, [documentId, cache]);

  const isLoading = !entry || entry.status === 'loading';

  return (
    <div className={styles.panel}>
      {isLoading && (
        <div className={styles.skeletonList} aria-label="Generating summary">
          {SKELETON_WIDTHS.map((w, i) => (
            <div key={i} className={styles.skeletonLine} style={{ width: `${w}%` }} />
          ))}
          <div className={styles.skeletonHint} aria-live="polite">
            {slow ? 'This is taking longer than usual…' : 'Generating summary…'}
          </div>
        </div>
      )}

      {entry?.status === 'error' && (
        <p className={styles.errorText}>{getErrorMessage(entry.error)}</p>
      )}

      {entry?.status === 'loaded' && !entry.summary && (
        <p className={styles.noContent}>No content to summarize.</p>
      )}

      {entry?.status === 'loaded' && entry.summary && (
        <ul className={styles.bulletList}>
          {parseBullets(entry.summary).map((b, i) => (
            <li key={i} className={styles.bullet}>
              {b}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
