import clsx from "clsx";
import { format, parseISO } from "date-fns";
import type { EvalRunSummary } from "../../api/types";

function formatTimestamp(value: string): string {
  try {
    return format(parseISO(value), "MMM d, yyyy, h:mm a");
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
      <p className="py-3 text-sm text-muted dark:text-muted-dark">
        No test runs yet. Run{" "}
        <code className="rounded bg-paper px-1.5 py-0.5 text-xs dark:bg-paper-dark">
          python scripts/run_eval.py
        </code>{" "}
        against the backend to create one.
      </p>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-rule text-sm text-muted dark:border-rule-dark dark:text-muted-dark">
          <th className="py-2.5 font-medium">Run</th>
          <th className="py-2.5 font-medium">Started</th>
          <th className="py-2.5 font-medium">Passage found</th>
          <th className="py-2.5 font-medium">Faithful to sources</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr
            key={run.run_id}
            onClick={() => onSelect(run.run_id)}
            className={clsx(
              "cursor-pointer border-b border-rule last:border-0 transition-colors hover:bg-paper dark:border-rule-dark dark:hover:bg-paper-dark",
              run.run_id === selectedRunId && "bg-paper font-semibold dark:bg-paper-dark",
            )}
          >
            <td className="py-2.5 tabular-nums">{run.run_id}</td>
            <td className="py-2.5 text-muted dark:text-muted-dark">{formatTimestamp(run.started_at)}</td>
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
