"use client";

import { useState } from "react";
import { Upload, FileText, CheckCircle, AlertCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { uploadDocument } from "@/lib/api";

interface FileStatus {
  file: File;
  status: "pending" | "uploading" | "done" | "error";
  message?: string;
}

export function FileUpload({ onUploadComplete }: { onUploadComplete: () => void }) {
  const [files, setFiles] = useState<FileStatus[]>([]);
  const [dragOver, setDragOver] = useState(false);

  const addFiles = (newFiles: FileList | null) => {
    if (!newFiles) return;
    const pdfFiles = Array.from(newFiles).filter((f) =>
      f.name.toLowerCase().endsWith(".pdf") ||
      f.name.toLowerCase().endsWith(".docx") ||
      f.name.toLowerCase().endsWith(".pptx")
    );
    setFiles((prev) => [
      ...prev,
      ...pdfFiles.map((file) => ({ file, status: "pending" as const })),
    ]);
  };

  const handleUpload = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].status !== "pending") continue;

      setFiles((prev) =>
        prev.map((f, idx) => (idx === i ? { ...f, status: "uploading" } : f))
      );

      try {
        const formData = new FormData();
        formData.append("file", files[i].file);
        await uploadDocument(formData);
        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "done", message: "Ingested" } : f))
        );
      } catch (e: unknown) {
        const message = e instanceof Error ? e.message : "Upload failed";
        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "error", message } : f))
        );
      }
    }
    onUploadComplete();
  };

  return (
    <div className="space-y-4">
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/25"}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => { e.preventDefault(); setDragOver(false); addFiles(e.dataTransfer.files); }}
      >
        <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
        <p className="text-sm text-muted-foreground mb-2">
          Drag & drop PDFs here, or{" "}
          <label className="text-primary cursor-pointer underline">
            browse
            <input type="file" className="hidden" multiple accept=".pdf,.docx,.pptx"
              onChange={(e) => addFiles(e.target.files)} />
          </label>
        </p>
      </div>

      {files.length > 0 && (
        <div className="space-y-2">
          {files.map((f, i) => (
            <Card key={i}>
              <CardContent className="flex items-center gap-3 py-3 px-4">
                <FileText className="h-4 w-4 shrink-0" />
                <span className="text-sm flex-1 truncate">{f.file.name}</span>
                <span className="text-xs text-muted-foreground">
                  {(f.file.size / 1024).toFixed(0)} KB
                </span>
                {f.status === "uploading" && <Loader2 className="h-4 w-4 animate-spin" />}
                {f.status === "done" && <CheckCircle className="h-4 w-4 text-green-500" />}
                {f.status === "error" && <AlertCircle className="h-4 w-4 text-destructive" />}
              </CardContent>
            </Card>
          ))}
          <Button onClick={handleUpload} disabled={files.every((f) => f.status !== "pending")}>
            Upload & Ingest ({files.filter((f) => f.status === "pending").length} files)
          </Button>
        </div>
      )}
    </div>
  );
}
