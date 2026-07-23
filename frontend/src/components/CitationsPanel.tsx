import type { Citation } from "../api/types";

export function CitationsPanel({ citations }: { citations: Citation[] }) {
  if (citations.length === 0) return null;

  return (
    <div className="mt-3 flex flex-col gap-2">
      <div className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        Sources
      </div>
      {citations.map((citation) => (
        <div
          key={citation.chunk_id}
          className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-sm dark:border-slate-800 dark:bg-slate-900"
        >
          <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
            <span className="font-medium text-slate-700 dark:text-slate-200">
              {citation.source_file}
              {citation.page !== null ? ` · p.${citation.page}` : ""}
            </span>
            {citation.retrieved_date && (
              <span className="text-xs text-slate-500 dark:text-slate-400">
                as of {citation.retrieved_date}
              </span>
            )}
          </div>
          <p className="mt-1 line-clamp-3 text-slate-600 dark:text-slate-400">{citation.text}</p>
          {citation.source_url && (
            <a
              href={citation.source_url}
              target="_blank"
              rel="noreferrer"
              className="mt-1 inline-block text-xs text-blue-600 hover:underline dark:text-blue-400"
            >
              View source
            </a>
          )}
        </div>
      ))}
    </div>
  );
}
