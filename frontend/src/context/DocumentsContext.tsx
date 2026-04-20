import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from 'react';
import { Document } from '@/types';
import { getDocuments } from '@/api/documents';
import { useUser } from '@/context/UserContext';

const RECENTS_CAP = 20;

// Keys are scoped to userId so different users on the same browser
// don't share pins/recents. When auth is added, userId comes from the
// JWT-backed UserContext — no changes needed here.
function pinnedKey(userId: string) { return `fetch-pinned-docs-${userId}`; }
function recentsKey(userId: string) { return `fetch-recent-docs-${userId}`; }

interface DocumentsContextValue {
  pinned: Document[];
  recents: Document[];
  togglePin: (doc: Document) => void;
  recordVisit: (doc: Document) => void;
}

const DocumentsContext = createContext<DocumentsContextValue | null>(null);

function readPinnedIds(key: string): Set<string> {
  try {
    const raw = localStorage.getItem(key);
    return new Set(raw ? JSON.parse(raw) : []);
  } catch {
    return new Set();
  }
}

function writePinnedIds(key: string, ids: Set<string>): void {
  localStorage.setItem(key, JSON.stringify([...ids]));
}

function readRecentDocs(key: string): Document[] {
  try {
    const raw = localStorage.getItem(key);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function writeRecentDocs(key: string, docs: Document[]): void {
  localStorage.setItem(key, JSON.stringify(docs));
}

export function DocumentsProvider({ children }: { children: ReactNode }) {
  const user = useUser();
  const userId = user?.id ?? 'anon';

  const [pinned, setPinned] = useState<Document[]>([]);
  const [recents, setRecents] = useState<Document[]>([]);

  // Reload whenever the active user changes (e.g. logout → login as someone else).
  useEffect(() => {
    const pk = pinnedKey(userId);
    const rk = recentsKey(userId);
    const pinnedIds = readPinnedIds(pk);

    getDocuments()
      .then((docs) => {
        const withPins = docs.filter((d) => pinnedIds.has(d.id)).map((d) => ({ ...d, isPinned: true }));
        setPinned(withPins);
      })
      .catch((err) => console.error('DocumentsContext: failed to load documents', err));

    setRecents(readRecentDocs(rk));
  }, [userId]);

  const togglePin = useCallback((doc: Document) => {
    const pk = pinnedKey(userId);
    const ids = readPinnedIds(pk);
    if (ids.has(doc.id)) {
      ids.delete(doc.id);
      setPinned((prev) => prev.filter((d) => d.id !== doc.id));
    } else {
      ids.add(doc.id);
      setPinned((prev) => [...prev, { ...doc, isPinned: true }]);
    }
    writePinnedIds(pk, ids);
  }, [userId]);

  const recordVisit = useCallback((doc: Document) => {
    const rk = recentsKey(userId);
    setRecents((prev) => {
      const next = [doc, ...prev.filter((d) => d.id !== doc.id)].slice(0, RECENTS_CAP);
      writeRecentDocs(rk, next);
      return next;
    });
  }, [userId]);

  return (
    <DocumentsContext.Provider value={{ pinned, recents, togglePin, recordVisit }}>
      {children}
    </DocumentsContext.Provider>
  );
}

export function useDocuments(): DocumentsContextValue {
  const ctx = useContext(DocumentsContext);
  if (!ctx) throw new Error('useDocuments must be used within DocumentsProvider');
  return ctx;
}
