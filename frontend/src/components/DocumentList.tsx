import type { DocumentSummary } from "../api/types";

export function DocumentList({ documents }: { documents: DocumentSummary[] }) {
  if (documents.length === 0) {
    return <p className="text-sm text-slate-500 dark:text-slate-400">No documents ingested yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2">
      {documents.map((doc) => (
        <div
          key={doc.doc_id}
          className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1 rounded-lg border border-slate-200 px-3 py-2 text-sm dark:border-slate-800"
        >
          <div>
            <div className="font-medium text-slate-800 dark:text-slate-200">{doc.source_file}</div>
            {doc.source_url && (
              <a
                href={doc.source_url}
                target="_blank"
                rel="noreferrer"
                className="text-xs text-blue-600 hover:underline dark:text-blue-400"
              >
                {doc.source_url}
              </a>
            )}
          </div>
          <div className="flex flex-col items-end text-xs text-slate-500 dark:text-slate-400">
            <span>{doc.chunk_count} chunks</span>
            {doc.retrieved_date && <span>as of {doc.retrieved_date}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
