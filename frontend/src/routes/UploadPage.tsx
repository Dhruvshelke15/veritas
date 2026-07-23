import { useCallback, useEffect, useState } from "react";
import { fetchDocuments, uploadDocument } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { DocumentList } from "../components/DocumentList";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await fetchDocuments());
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setError(null);
    try {
      await uploadDocument(file);
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl px-4 py-10">
      <h1 className="font-display text-2xl font-medium text-stone-900 dark:text-stone-100">
        Documents
      </h1>
      <p className="mt-1.5 text-sm text-stone-500 dark:text-stone-400">
        Upload source documents (.pdf, .md, .txt) to ground answers in.
      </p>

      <div className="mt-6">
        <UploadDropzone onUpload={handleUpload} uploading={uploading} />
      </div>

      {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

      <div className="mt-10">
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
          Ingested documents
        </h2>
        {loading ? (
          <p className="text-sm text-stone-500 dark:text-stone-400">Loading…</p>
        ) : (
          <DocumentList documents={documents} />
        )}
      </div>
    </div>
  );
}
