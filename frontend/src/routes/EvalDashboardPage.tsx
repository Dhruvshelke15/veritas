import { useEffect, useMemo, useState } from "react";
import { motion } from "motion/react";
import { fetchEvalRunDetail, fetchEvalRuns } from "../api/client";
import type { EvalRunDetail, EvalRunSummary } from "../api/types";
import { StatTile } from "../components/eval/StatTile";
import { CategoryAccuracyBar } from "../components/eval/CategoryAccuracyBar";
import { RunsTable } from "../components/eval/RunsTable";
import { Target, Sparkles } from "lucide-react";

const sectionMotion = (delay: number) => ({
  initial: { opacity: 0, y: 10 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.3, delay },
});

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
    <div className="mx-auto max-w-3xl px-4 py-10">
      <h1 className="font-display text-2xl font-medium text-stone-900 dark:text-stone-100">
        Evaluation dashboard
      </h1>
      <p className="mt-1.5 text-sm text-stone-500 dark:text-stone-400">
        Retrieval hit rate, answer faithfulness, and classifier accuracy across eval runs.
      </p>

      {error && <p className="mt-4 text-sm text-red-600 dark:text-red-400">{error}</p>}

      {loading ? (
        <p className="mt-6 text-sm text-stone-500 dark:text-stone-400">Loading…</p>
      ) : (
        <>
          <motion.div {...sectionMotion(0)} className="mt-6 flex gap-3">
            <StatTile
              icon={Target}
              label="Retrieval hit rate"
              value={latest?.retrieval_hit_rate ?? null}
              format={(v) => `${Math.round(v * 100)}%`}
              trend={hitRateTrend.length >= 2 ? hitRateTrend : undefined}
            />
            <StatTile
              icon={Sparkles}
              label="Mean faithfulness"
              value={latest?.mean_faithfulness ?? null}
              format={(v) => `${v.toFixed(2)} / 5`}
              trend={faithfulnessTrend.length >= 2 ? faithfulnessTrend : undefined}
            />
          </motion.div>

          <motion.div {...sectionMotion(0.08)} className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
              Classifier accuracy by category {detail ? `(run #${detail.run.run_id})` : ""}
            </h2>
            <div className="rounded-2xl border border-stone-200 bg-white px-5 py-4 dark:border-stone-800 dark:bg-stone-900">
              {detail?.run.classifier_accuracy ? (
                <CategoryAccuracyBar accuracy={detail.run.classifier_accuracy} />
              ) : (
                <p className="text-sm text-stone-500 dark:text-stone-400">No classifier data for this run.</p>
              )}
            </div>
          </motion.div>

          <motion.div {...sectionMotion(0.16)} className="mt-8">
            <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
              Runs
            </h2>
            <div className="rounded-2xl border border-stone-200 bg-white px-5 py-2 dark:border-stone-800 dark:bg-stone-900">
              <RunsTable runs={runs} selectedRunId={selectedRunId} onSelect={setSelectedRunId} />
            </div>
          </motion.div>
        </>
      )}
    </div>
  );
}
