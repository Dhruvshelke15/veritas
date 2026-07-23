import { useEffect, useMemo, useState } from "react";
import { fetchEvalRunDetail, fetchEvalRuns } from "../api/client";
import type { EvalRunDetail, EvalRunSummary } from "../api/types";
import { StatTile } from "../components/eval/StatTile";
import { CategoryAccuracyBar } from "../components/eval/CategoryAccuracyBar";
import { RunsTable } from "../components/eval/RunsTable";

export function EvalDashboardPage() {
  const [runs, setRuns] = useState<EvalRunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
  const [detail, setDetail] = useState<EvalRunDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchEvalRuns()
      .then((data) => {
        setRuns(data);
        if (data.length > 0) setSelectedRunId(data[0].run_id);
      })
      .catch((err) => setError(err instanceof Error ? err.message : String(err)))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedRunId === null) return;
    fetchEvalRunDetail(selectedRunId)
      .then(setDetail)
      .catch((err) => setError(err instanceof Error ? err.message : String(err)));
  }, [selectedRunId]);

  // Chronological order (oldest -> newest) for sparklines; `runs` is newest-first.
  const chronological = useMemo(() => [...runs].reverse(), [runs]);
  const hitRateTrend = chronological
    .map((r) => r.retrieval_hit_rate)
    .filter((v): v is number => v !== null);
  const faithfulnessTrend = chronological
    .map((r) => r.mean_faithfulness)
    .filter((v): v is number => v !== null);

  const latest = runs[0] ?? null;

  return (
    <div className="mx-auto max-w-3xl px-4 py-8">
      <h1 className="text-xl font-semibold text-slate-900 dark:text-slate-100">Evaluation dashboard</h1>
      <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">
        Retrieval hit rate, answer faithfulness, and classifier accuracy across eval runs.
      </p>

      {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {loading ? (
        <p className="mt-6 text-sm text-slate-500 dark:text-slate-400">Loading…</p>
      ) : (
        <>
          <div className="mt-6 flex gap-3">
            <StatTile
              label="Retrieval hit rate"
              value={latest?.retrieval_hit_rate !== null && latest?.retrieval_hit_rate !== undefined ? `${(latest.retrieval_hit_rate * 100).toFixed(0)}%` : "—"}
              trend={hitRateTrend.length >= 2 ? hitRateTrend : undefined}
            />
            <StatTile
              label="Mean faithfulness"
              value={latest?.mean_faithfulness !== null && latest?.mean_faithfulness !== undefined ? `${latest.mean_faithfulness.toFixed(2)} / 5` : "—"}
              trend={faithfulnessTrend.length >= 2 ? faithfulnessTrend : undefined}
            />
          </div>

          <div className="mt-8">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Classifier accuracy by category {detail ? `(run #${detail.run.run_id})` : ""}
            </h2>
            {detail?.run.classifier_accuracy ? (
              <CategoryAccuracyBar accuracy={detail.run.classifier_accuracy} />
            ) : (
              <p className="text-sm text-slate-500 dark:text-slate-400">No classifier data for this run.</p>
            )}
          </div>

          <div className="mt-8">
            <h2 className="mb-3 text-sm font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
              Runs
            </h2>
            <RunsTable runs={runs} selectedRunId={selectedRunId} onSelect={setSelectedRunId} />
          </div>
        </>
      )}
    </div>
  );
}
