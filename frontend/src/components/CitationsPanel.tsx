import { useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { format, parseISO } from "date-fns";
import type { Citation } from "../api/types";

function formatDate(value: string): string {
  try {
    return format(parseISO(value), "MMM d, yyyy");
  } catch {
    return value;
  }
}

export function CitationsPanel({ citations }: { citations: Citation[] }) {
  const [expanded, setExpanded] = useState(false);

  if (citations.length === 0) return null;
  const noun = citations.length === 1 ? "source" : "sources";

  return (
    <div className="mt-5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="text-sm font-semibold text-form underline-offset-4 hover:underline dark:text-form-dark"
      >
        {expanded ? `Hide ${noun}` : `Show the ${citations.length} ${noun}`}
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: "easeInOut" }}
            className="overflow-hidden"
          >
            <ul className="mt-3 flex flex-col gap-3">
              {citations.map((citation) => (
                <li
                  key={citation.chunk_id}
                  className="border-l-2 border-form bg-sheet py-3 pl-4 pr-4 dark:border-form-dark dark:bg-sheet-dark"
                >
                  <p className="text-sm font-semibold">
                    {citation.source_file}
                    {citation.page !== null && <span className="font-normal text-muted dark:text-muted-dark">, page {citation.page}</span>}
                  </p>
                  {citation.retrieved_date && (
                    <p className="text-xs text-muted dark:text-muted-dark">As of {formatDate(citation.retrieved_date)}</p>
                  )}
                  <p className="mt-2 font-serif text-[0.9375rem] leading-relaxed">
                    <mark className="bg-highlight box-decoration-clone px-0.5 text-ink dark:bg-highlight-dark dark:text-ink-dark">
                      {citation.text}
                    </mark>
                  </p>
                  {citation.source_url && (
                    <a
                      href={citation.source_url}
                      target="_blank"
                      rel="noreferrer"
                      className="mt-2 inline-block text-sm font-semibold text-form underline-offset-4 hover:underline dark:text-form-dark"
                    >
                      Open the original
                    </a>
                  )}
                </li>
              ))}
            </ul>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
