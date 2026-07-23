import { useState } from "react";
import { ChevronDown, ExternalLink, FileCheck } from "lucide-react";
import type { Citation } from "../api/types";

export function CitationsPanel({ citations }: { citations: Citation[] }) {
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;

  return (
    <div className="mt-3.5 border-t border-stone-100 pt-3 dark:border-stone-800">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex items-center gap-1.5 text-xs font-medium text-stone-500 transition-colors hover:text-brand-600 dark:text-stone-400 dark:hover:text-brand-300"
      >
        <FileCheck className="h-3.5 w-3.5" strokeWidth={2.25} />
        {citations.length} verified {citations.length === 1 ? "source" : "sources"}
        <ChevronDown
          className={`h-3.5 w-3.5 transition-transform ${expanded ? "rotate-180" : ""}`}
          strokeWidth={2.25}
        />
      </button>

      {expanded && (
        <div className="mt-2.5 flex flex-col gap-2">
          {citations.map((citation) => (
            <div
              key={citation.chunk_id}
              className="rounded-xl border border-stone-200/80 bg-stone-50 px-3.5 py-2.5 text-sm dark:border-stone-800 dark:bg-stone-950/40"
            >
              <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-1">
                <span className="font-medium text-stone-700 dark:text-stone-200">
                  {citation.source_file}
                  {citation.page !== null ? ` · p.${citation.page}` : ""}
                </span>
                {citation.retrieved_date && (
                  <span className="rounded-full bg-accent-500/10 px-2 py-0.5 text-xs font-medium text-accent-600 dark:text-accent-400">
                    as of {citation.retrieved_date}
                  </span>
                )}
              </div>
              <p className="mt-1.5 line-clamp-3 text-stone-600 dark:text-stone-400">{citation.text}</p>
              {citation.source_url && (
                <a
                  href={citation.source_url}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-1.5 inline-flex items-center gap-1 text-xs font-medium text-brand-600 hover:text-brand-700 hover:underline dark:text-brand-300 dark:hover:text-brand-200"
                >
                  View source
                  <ExternalLink className="h-3 w-3" strokeWidth={2} />
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
