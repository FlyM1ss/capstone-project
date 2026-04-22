import { useEffect, useState } from 'react';
import {
  type DocumentSummary,
  getDocumentSummary,
} from '@/api/documents';
import { ApiError } from '@/api/client';
import styles from './DocumentSummaryPanel.module.scss';

interface Props {
  documentId: string;
}

type State =
  | { kind: 'loading' }
  | { kind: 'empty' }
  | { kind: 'loaded'; bullets: string[]; cached: boolean }
  | { kind: 'error'; message: string };

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
  const [state, setState] = useState<State>({ kind: 'loading' });
  const [slow, setSlow] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setState({ kind: 'loading' });
    setSlow(false);
    const slowTimer = window.setTimeout(() => {
      if (!cancelled) setSlow(true);
    }, SLOW_CALL_THRESHOLD_MS);

    getDocumentSummary(documentId)
      .then((res: DocumentSummary) => {
        if (cancelled) return;
        if (!res.summary) {
          setState({ kind: 'empty' });
          return;
        }
        setState({
          kind: 'loaded',
          bullets: parseBullets(res.summary),
          cached: res.cached,
        });
      })
      .catch((err: unknown) => {
        if (cancelled) return;
        setState({ kind: 'error', message: getErrorMessage(err) });
      });

    return () => {
      cancelled = true;
      window.clearTimeout(slowTimer);
    };
  }, [documentId]);

  return (
    <div className={styles.panel}>
      {state.kind === 'loading' && (
        <div className={styles.skeletonList} aria-label="Generating summary">
          {SKELETON_WIDTHS.map((w, i) => (
            <div key={i} className={styles.skeletonLine} style={{ width: `${w}%` }} />
          ))}
          <div className={styles.skeletonHint} aria-live="polite">
            {slow ? 'This is taking longer than usual…' : 'Generating summary…'}
          </div>
        </div>
      )}

      {state.kind === 'empty' && (
        <p className={styles.noContent}>No content to summarize.</p>
      )}

      {state.kind === 'error' && (
        <p className={styles.errorText}>{state.message}</p>
      )}

      {state.kind === 'loaded' && (
        <ul className={styles.bulletList}>
          {state.bullets.map((b, i) => (
            <li key={i} className={styles.bullet}>
              {b}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
