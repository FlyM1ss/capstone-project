import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  type DocumentDetail,
  type DocumentChunk,
  getDocumentById,
  getDocumentChunks,
  getDocumentFileUrl,
  getDocumentPreviewUrl,
} from '@/api/documents';
import FileTypeBadge from '@/components/FileTypeBadge/FileTypeBadge';
import DocumentSummaryPanel from '@/components/DocumentSummaryPanel/DocumentSummaryPanel';
import { timeAgo } from '@/utils/timeAgo';
import type { FileType } from '@/types';
import styles from './DocumentPage.module.scss';

type Tab = 'preview' | 'text';

function fileTypeFromDocType(docType: string): FileType {
  const lower = docType.toLowerCase();
  if (lower.includes('docx') || lower.includes('word')) return 'docx';
  if (lower.includes('pptx') || lower.includes('powerpoint') || lower.includes('ppt')) return 'pptx';
  return 'pdf';
}

export default function DocumentPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [doc, setDoc] = useState<DocumentDetail | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [tab, setTab] = useState<Tab>('preview');
  const [downloading, setDownloading] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);

    Promise.all([getDocumentById(id), getDocumentChunks(id)])
      .then(([docData, chunksData]) => {
        setDoc(docData);
        setChunks(chunksData);
      })
      .catch((err: Error) => {
        setError(err.message || 'Failed to load document');
      })
      .finally(() => setLoading(false));
  }, [id]);

  const handleDownload = async () => {
    if (!id || !doc) return;
    setDownloading(true);
    try {
      const res = await fetch(getDocumentFileUrl(id));
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const ext = fileTypeFromDocType(doc.doc_type);
      const hasExt = doc.title.toLowerCase().endsWith(`.${ext}`);
      a.download = hasExt ? doc.title : `${doc.title}.${ext}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silently ignore — nothing useful to show the user
    } finally {
      setDownloading(false);
    }
  };

  if (loading) {
    return (
      <div className={styles.page}>
        <div className={styles.centered}>
          <div className={styles.spinner} />
          <span className={styles.loadingText}>Loading document…</span>
        </div>
      </div>
    );
  }

  if (error || !doc) {
    return (
      <div className={styles.page}>
        <button className={styles.backBtn} onClick={() => navigate(-1)}>
          ← Back
        </button>
        <div className={styles.centered}>
          <p className={styles.errorText}>{error ?? 'Document not found'}</p>
        </div>
      </div>
    );
  }

  const fileType = fileTypeFromDocType(doc.doc_type);
  const previewUrl = id ? getDocumentPreviewUrl(id) : '';

  return (
    <div className={styles.page}>
      <button className={styles.backBtn} onClick={() => navigate(-1)}>
        ← Back
      </button>

      <div className={styles.header}>
        <div className={styles.titleRow}>
          <h1 className={styles.title}>{doc.title}</h1>
          <div className={styles.titleActions}>
            <FileTypeBadge fileType={fileType} />
            <button
              className={styles.downloadBtn}
              onClick={handleDownload}
              disabled={downloading}
            >
              {downloading ? 'Downloading…' : '↓ Download'}
            </button>
          </div>
        </div>
        <div className={styles.meta}>
          {doc.author && <span>{doc.author}</span>}
          {doc.author && <span className={styles.dot}>·</span>}
          <span>{doc.category}</span>
          {doc.page_count != null && (
            <>
              <span className={styles.dot}>·</span>
              <span>{doc.page_count} pages</span>
            </>
          )}
          <span className={styles.dot}>·</span>
          <span>{timeAgo(doc.created_at)}</span>
        </div>
      </div>

      <div className={styles.splitLayout}>
        <div className={styles.mainColumn}>
          <div className={styles.tabBar}>
            <button
              className={`${styles.tabBtn} ${tab === 'preview' ? styles.tabBtnActive : ''}`}
              onClick={() => setTab('preview')}
            >
              Preview
            </button>
            <button
              className={`${styles.tabBtn} ${tab === 'text' ? styles.tabBtnActive : ''}`}
              onClick={() => setTab('text')}
            >
              Text Content
            </button>
          </div>

          <div className={styles.contentArea}>
            {tab === 'preview' && (
              <iframe
                src={previewUrl}
                className={styles.pdfFrame}
                title={doc.title}
              />
            )}

            {tab === 'text' && (
              <div className={styles.textContent}>
                {chunks.length === 0 ? (
                  <p className={styles.noChunks}>No text content available for this document.</p>
                ) : (
                  chunks.map((chunk) => (
                    <p key={chunk.chunk_index} className={styles.chunk}>
                      {chunk.content}
                    </p>
                  ))
                )}
              </div>
            )}
          </div>
        </div>

        <aside className={styles.sideColumn}>
          <div className={styles.summaryHeader}>AI Summary</div>
          <div className={styles.summaryContent}>
            {id && <DocumentSummaryPanel documentId={id} />}
          </div>
        </aside>
      </div>
    </div>
  );
}
