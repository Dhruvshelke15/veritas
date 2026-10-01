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
      toast.success(`Added ${result.filename}`, {
        description: `${result.chunks_indexed} passages are now searchable.`,
      });
      await reload();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">Sources</h1>
      <p className="mt-2 max-w-xl font-serif text-muted dark:text-muted-dark">
        The documents Veritas answers from. Add a PDF, Markdown, or text file to include it in future answers.
      </p>

      <div className="mt-8 max-w-3xl">
        <UploadDropzone onUpload={handleUpload} uploading={uploading} />
      </div>

      <h2 className="mt-12 text-lg font-bold">
        In the library{!loading && documents.length > 0 ? ` (${documents.length})` : ""}
      </h2>
      <div className="mt-3 max-w-3xl">
        {loading ? (
          <p className="text-sm text-muted dark:text-muted-dark">Loading the library</p>
        ) : (
          <DocumentList documents={documents} />
        )}
      </div>
    </div>
  );
}
