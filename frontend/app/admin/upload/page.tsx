"use client";

import { useEffect, useState } from "react";
import { FileUpload } from "@/components/file-upload";
import { listDocuments, type DocumentInfo } from "@/lib/api";

export default function AdminUploadPage() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);

  const fetchDocs = () => {
    listDocuments().then(setDocuments).catch(console.error);
  };

  useEffect(fetchDocs, []);

  return (
    <div className="max-w-3xl mx-auto px-6 py-8">
      <div className="mb-6">
        <a href="/" className="text-sm text-muted-foreground hover:text-foreground">
          &larr; Back to search
        </a>
      </div>
      <h1 className="text-2xl font-bold mb-6">Document Upload</h1>

      <FileUpload onUploadComplete={fetchDocs} />

      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-3">
          Ingested Documents ({documents.length})
        </h2>
        <div className="border rounded-lg divide-y">
          {documents.map((doc) => (
            <div key={doc.id} className="px-4 py-3 flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">{doc.title}</p>
                <p className="text-xs text-muted-foreground">
                  {doc.doc_type.toUpperCase()} &middot; {doc.chunk_count} chunks &middot; {doc.category}
                </p>
              </div>
              <span className="text-xs text-muted-foreground">
                {new Date(doc.created_at).toLocaleDateString()}
              </span>
            </div>
          ))}
          {documents.length === 0 && (
            <p className="px-4 py-6 text-sm text-muted-foreground text-center">
              No documents ingested yet. Upload some above.
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
