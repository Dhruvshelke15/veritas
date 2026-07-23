import type { EvalRunSummary } from "../../api/types";

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
      <p className="text-sm text-slate-500 dark:text-slate-400">
        No eval runs yet. Run <code className="rounded bg-slate-100 px-1 dark:bg-slate-800">python scripts/run_eval.py</code> against the backend.
      </p>
    );
  }

  return (
    <table className="w-full text-left text-sm">
      <thead>
        <tr className="border-b border-slate-200 text-xs uppercase tracking-wide text-slate-500 dark:border-slate-800 dark:text-slate-400">
          <th className="py-2 font-medium">Run</th>
          <th className="py-2 font-medium">Started</th>
          <th className="py-2 font-medium">Hit rate</th>
          <th className="py-2 font-medium">Faithfulness</th>
        </tr>
      </thead>
      <tbody>
        {runs.map((run) => (
          <tr
            key={run.run_id}
            onClick={() => onSelect(run.run_id)}
            className={`cursor-pointer border-b border-slate-100 hover:bg-slate-50 dark:border-slate-900 dark:hover:bg-slate-900 ${
              run.run_id === selectedRunId ? "bg-slate-50 dark:bg-slate-900" : ""
            }`}
          >
            <td className="py-2 tabular-nums">#{run.run_id}</td>
            <td className="py-2 text-slate-500 dark:text-slate-400">{run.started_at}</td>
            <td className="py-2 tabular-nums">
              {run.retrieval_hit_rate !== null ? `${(run.retrieval_hit_rate * 100).toFixed(0)}%` : "—"}
            </td>
            <td className="py-2 tabular-nums">
              {run.mean_faithfulness !== null ? `${run.mean_faithfulness.toFixed(2)} / 5` : "—"}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
