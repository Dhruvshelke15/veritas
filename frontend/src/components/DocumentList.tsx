import { FileText } from "lucide-react";
import { motion } from "motion/react";
import { format, parseISO } from "date-fns";
import type { DocumentSummary } from "../api/types";

function formatDate(value: string): string {
  try {
    return format(parseISO(value), "MMM d, yyyy");
  } catch {
    return value;
  }
}

export function DocumentList({ documents }: { documents: DocumentSummary[] }) {
  if (documents.length === 0) {
    return <p className="text-sm text-stone-500 dark:text-stone-400">No documents ingested yet.</p>;
  }

  return (
    <div className="flex flex-col gap-2.5">
      {documents.map((doc, i) => (
        <motion.div
          key={doc.doc_id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2, delay: i * 0.05 }}
          className="flex items-start gap-3 rounded-xl border border-stone-200 bg-white px-4 py-3 transition-colors hover:border-brand-200 dark:border-stone-800 dark:bg-stone-900 dark:hover:border-brand-700"
        >
          <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-brand-50 dark:bg-brand-900">
            <FileText className="h-4 w-4 text-brand-600 dark:text-brand-300" strokeWidth={2} />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
              <span className="truncate text-sm font-medium text-stone-800 dark:text-stone-200">
                {doc.source_file}
              </span>
              <span className="shrink-0 rounded-full bg-stone-100 px-2 py-0.5 text-xs font-medium text-stone-500 dark:bg-stone-800 dark:text-stone-400">
                {doc.chunk_count} chunks
              </span>
            </div>
            {doc.source_url && (
              <a
                href={doc.source_url}
                target="_blank"
                rel="noreferrer"
                className="mt-0.5 block truncate text-xs text-brand-600 hover:underline dark:text-brand-300"
              >
                {doc.source_url}
              </a>
            )}
            {doc.retrieved_date && (
              <span className="mt-1 inline-block text-xs text-stone-400 dark:text-stone-500">
                as of {formatDate(doc.retrieved_date)}
              </span>
            )}
          </div>
        </motion.div>
      ))}
    </div>
  );
}
