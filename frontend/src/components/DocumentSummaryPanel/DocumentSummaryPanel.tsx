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

export default function DocumentSummaryPanel({ documentId }: Props) {
  const [state, setState] = useState<State>({ kind: 'loading' });

  useEffect(() => {
    let cancelled = false;
    setState({ kind: 'loading' });

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
        const message =
          err instanceof ApiError
            ? err.body?.error_code === 'summarizer_unavailable'
              ? 'Summary service is unavailable right now.'
              : err.detail ?? 'Could not load summary.'
            : 'Could not load summary.';
        setState({ kind: 'error', message });
      });

    return () => {
      cancelled = true;
    };
  }, [documentId]);

  return (
    <div className={styles.panel}>
      {state.kind === 'loading' && (
        <div className={styles.skeletonList} aria-label="Generating summary">
          <div className={styles.skeletonLine} style={{ width: '92%' }} />
          <div className={styles.skeletonLine} style={{ width: '78%' }} />
          <div className={styles.skeletonLine} style={{ width: '85%' }} />
          <div className={styles.skeletonLine} style={{ width: '70%' }} />
          <div className={styles.skeletonLine} style={{ width: '88%' }} />
          <div className={styles.skeletonHint}>Generating summary…</div>
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
