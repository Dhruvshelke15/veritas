import clsx from "clsx";
import { format, parseISO } from "date-fns";
import type { EvalRunSummary } from "../../api/types";

function formatTimestamp(value: string): string {
  try {
    return format(parseISO(value), "MMM d, yyyy · h:mm a");
  } catch {
    return value;
  }
}

export function RunsTable({
  runs,
  selectedRunId,
  onSelect,
}: {
  runs: EvalRunSummary[];
  selectedRunId: number | null;
  onSelect: (runId: number) => void;
}) {
  if (runs.length === 0) {
    return (
      <p className="py-3 text-sm text-stone-500 dark:text-stone-400">
        No eval runs yet. Run{" "}
        <code className="rounded bg-stone-100 px-1.5 py-0.5 text-xs dark:bg-stone-800">
          python scripts/run_eval.py
        </code>{" "}
        against the backend.
      </p>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-stone-200 text-xs uppercase tracking-wide text-stone-500 dark:border-stone-800 dark:text-stone-400">
          <th className="py-2.5 font-medium">Run</th>
          <th className="py-2.5 font-medium">Started</th>
          <th className="py-2.5 font-medium">Hit rate</th>
          <th className="py-2.5 font-medium">Faithfulness</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr
            key={run.run_id}
            onClick={() => onSelect(run.run_id)}
            className={clsx(
              "cursor-pointer border-b border-stone-100 last:border-0 transition-colors duration-200 hover:bg-brand-50 dark:border-stone-900 dark:hover:bg-brand-900/30",
              run.run_id === selectedRunId && "bg-brand-50 dark:bg-brand-900/30",
            )}
          >
            <td className="py-2.5 tabular-nums">#{run.run_id}</td>
            <td className="py-2.5 text-stone-500 dark:text-stone-400">{formatTimestamp(run.started_at)}</td>
            <td className="py-2.5 tabular-nums">
              {run.retrieval_hit_rate !== null ? `${(run.retrieval_hit_rate * 100).toFixed(0)}%` : "—"}
            </td>
            <td className="py-2.5 tabular-nums">
              {run.mean_faithfulness !== null ? `${run.mean_faithfulness.toFixed(2)} / 5` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
