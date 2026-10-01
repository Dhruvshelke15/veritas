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
    <div className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
      <h1 className="text-2xl font-bold tracking-tight">Answer quality</h1>
      <p className="mt-2 max-w-xl font-serif text-muted dark:text-muted-dark">
        Every test run asks a fixed set of questions with known answers, then measures how often the right
        passage was found and how closely answers stick to their sources.
      </p>

      {error && <p className="mt-4 text-sm text-refusal dark:text-refusal-dark">{error}</p>}

      {loading ? (
        <p className="mt-6 text-sm text-muted dark:text-muted-dark">Loading test runs</p>
      ) : (
        <>
          <div className="mt-8 grid max-w-3xl gap-3 sm:grid-cols-2">
            <StatTile
              label="Found the right passage"
              value={latest?.retrieval_hit_rate ?? null}
              format={(v) => `${Math.round(v * 100)}%`}
              trend={hitRateTrend.length >= 2 ? hitRateTrend : undefined}
            />
            <StatTile
              label="Faithful to sources"
              value={latest?.mean_faithfulness ?? null}
              format={(v) => `${v.toFixed(2)} / 5`}
              trend={faithfulnessTrend.length >= 2 ? faithfulnessTrend : undefined}
            />
          </div>

          <section className="mt-10 max-w-3xl">
            <h2 className="mb-3 text-lg font-bold">
              Question sorting accuracy{detail ? `, run ${detail.run.run_id}` : ""}
            </h2>
            <div className="overflow-x-auto rounded-md border border-rule bg-sheet px-5 py-4 dark:border-rule-dark dark:bg-sheet-dark">
              {detail?.run.classifier_accuracy ? (
                <CategoryAccuracyBar accuracy={detail.run.classifier_accuracy} />
              ) : (
                <p className="text-sm text-muted dark:text-muted-dark">This run has no question-sorting results.</p>
              )}
            </div>
          </section>

          <section className="mt-10 max-w-3xl">
            <h2 className="mb-3 text-lg font-bold">
              Test runs
            </h2>
            <div className="overflow-x-auto rounded-md border border-rule bg-sheet px-5 py-2 dark:border-rule-dark dark:bg-sheet-dark">
              <RunsTable runs={runs} selectedRunId={selectedRunId} onSelect={setSelectedRunId} />
            </div>
          </section>
        </>
      )}
    </div>
  );
}
