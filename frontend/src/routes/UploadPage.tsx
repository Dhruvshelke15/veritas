import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { fetchDocuments, uploadDocument } from "../api/client";
import type { DocumentSummary } from "../api/types";
import { DocumentList } from "../components/DocumentList";
import { UploadDropzone } from "../components/UploadDropzone";

export function UploadPage() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [uploading, setUploading] = useState(false);
  const [loading, setLoading] = useState(true);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setDocuments(await fetchDocuments());
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
  }, [reload]);

  const handleUpload = async (file: File) => {
    setUploading(true);
    try {
      const result = await uploadDocument(file);
      toast.success(`${result.filename} ingested`, {
        description: `${result.chunks_indexed} chunks indexed`,
      });
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
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
