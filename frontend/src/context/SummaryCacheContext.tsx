import {
  createContext,
  useContext,
  useRef,
  useSyncExternalStore,
  ReactNode,
} from 'react';
import { type DocumentSummary, getDocumentSummary } from '@/api/documents';

// Keeps generated/in-flight summaries keyed by documentId so the Summarize
// button on the results page and the panel on the document page share one
// request. Navigating mid-fetch joins the existing Promise instead of
// triggering a second Cohere call.
export type SummaryEntry =
  | { status: 'loading' }
  | { status: 'loaded'; summary: string | null; cached: boolean; generatedAt: string | null }
  | { status: 'error'; error: unknown };

interface SummaryCacheStore {
  get(id: string): SummaryEntry | undefined;
  ensure(id: string): Promise<DocumentSummary>;
  subscribe(id: string, listener: () => void): () => void;
}

const SummaryCacheContext = createContext<SummaryCacheStore | null>(null);

export function SummaryCacheProvider({ children }: { children: ReactNode }) {
  const entries = useRef(new Map<string, SummaryEntry>());
  const inflight = useRef(new Map<string, Promise<DocumentSummary>>());
  const listeners = useRef(new Map<string, Set<() => void>>());

  const storeRef = useRef<SummaryCacheStore | null>(null);
  if (!storeRef.current) {
    const notify = (id: string) => {
      listeners.current.get(id)?.forEach((l) => l());
    };

    storeRef.current = {
      get(id) {
        return entries.current.get(id);
      },

      ensure(id) {
        const existing = inflight.current.get(id);
        if (existing) return existing;

        const current = entries.current.get(id);
        if (current?.status === 'loaded') {
          return Promise.resolve({
            document_id: id,
            summary: current.summary,
            cached: current.cached,
            generated_at: current.generatedAt,
          });
        }

        entries.current.set(id, { status: 'loading' });
        notify(id);

        const promise = getDocumentSummary(id)
          .then((res) => {
            entries.current.set(id, {
              status: 'loaded',
              summary: res.summary,
              cached: res.cached,
              generatedAt: res.generated_at,
            });
            notify(id);
            return res;
          })
          .catch((err) => {
            entries.current.set(id, { status: 'error', error: err });
            notify(id);
            throw err;
          })
          .finally(() => {
            inflight.current.delete(id);
          });

        inflight.current.set(id, promise);
        return promise;
      },

      subscribe(id, listener) {
        let set = listeners.current.get(id);
        if (!set) {
          set = new Set();
          listeners.current.set(id, set);
        }
        set.add(listener);
        return () => {
          set!.delete(listener);
          if (set!.size === 0) listeners.current.delete(id);
        };
      },
    };
  }

  return (
    <SummaryCacheContext.Provider value={storeRef.current}>
      {children}
    </SummaryCacheContext.Provider>
  );
}

export function useSummaryCache(): SummaryCacheStore {
  const ctx = useContext(SummaryCacheContext);
  if (!ctx) throw new Error('useSummaryCache must be used within SummaryCacheProvider');
  return ctx;
}

// Reactive read of a single document's entry. Does NOT trigger a fetch —
// callers wanting to start work call `ensure()` explicitly.
export function useDocumentSummary(documentId: string | null | undefined): SummaryEntry | undefined {
  const store = useSummaryCache();
  return useSyncExternalStore(
    (listener) => (documentId ? store.subscribe(documentId, listener) : () => {}),
    () => (documentId ? store.get(documentId) : undefined),
    () => (documentId ? store.get(documentId) : undefined),
  );
}
