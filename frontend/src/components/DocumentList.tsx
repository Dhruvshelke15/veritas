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
    return (
      <p className="text-sm text-muted dark:text-muted-dark">
        No documents yet. Add a USCIS or ICE document above so Veritas has something to answer from.
      </p>
    );
  }

  return (
    <ul className="border-t border-rule dark:border-rule-dark">
      {documents.map((doc) => (
        <li
          key={doc.doc_id}
          className="flex flex-col gap-1 border-b border-rule py-3.5 sm:flex-row sm:items-baseline sm:justify-between sm:gap-6 dark:border-rule-dark"
        >
          <div className="min-w-0">
            <p className="truncate font-semibold">{doc.source_file}</p>
            {doc.source_url && (
              <a
                href={doc.source_url}
                target="_blank"
                rel="noreferrer"
                className="block truncate text-sm text-form underline-offset-2 hover:underline dark:text-form-dark"
              >
                {doc.source_url}
              </a>
            )}
          </div>
          <p className="shrink-0 text-sm tabular-nums text-muted dark:text-muted-dark">
            {doc.chunk_count} passages
            {doc.retrieved_date && <>, as of {formatDate(doc.retrieved_date)}</>}
          </p>
        </li>
      ))}
    </ul>
  );
}
