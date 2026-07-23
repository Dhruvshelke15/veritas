import { useEffect, useState } from "react";
import type { LucideIcon } from "lucide-react";
import { animate, motion, useMotionValue, useMotionValueEvent } from "motion/react";

const ACCENT = "text-[#2a78d6] dark:text-[#3987e5]";
const DE_EMPHASIS = "text-stone-300 dark:text-stone-700";

function sparklinePoints(values: number[], width: number, height: number): [number, number][] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  return values.map((v, i) => [i * step, height - ((v - min) / span) * height]);
}

function useCountUp(target: number | null, duration = 0.8): number {
  const motionValue = useMotionValue(0);
  const [display, setDisplay] = useState(0);

  useMotionValueEvent(motionValue, "change", (latest) => setDisplay(latest));

  useEffect(() => {
    if (target === null) return;
    const controls = animate(motionValue, target, { duration, ease: "easeOut" });
    return controls.stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [target]);

  return display;
}

export function StatTile({
  icon: Icon,
  label,
  value,
  format,
  trend,
}: {
  icon: LucideIcon;
  label: string;
  value: number | null;
  format: (v: number) => string;
  trend?: number[];
}) {
  const width = 96;
  const height = 28;
  const hasTrend = trend && trend.length >= 2;
  const points = hasTrend ? sparklinePoints(trend!, width, height) : [];
  const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = points[points.length - 1];
  const animated = useCountUp(value);

  return (
    <div className="flex flex-1 flex-col gap-2 rounded-2xl border border-stone-200 bg-white px-4 py-3.5 dark:border-stone-800 dark:bg-stone-900">
      <span className="flex items-center gap-1.5 text-xs font-semibold uppercase tracking-wide text-stone-500 dark:text-stone-400">
        <Icon className="h-3.5 w-3.5" strokeWidth={2.25} />
        {label}
      </span>
      <div className="flex items-end justify-between gap-3">
        <span className="text-2xl font-semibold text-stone-900 dark:text-stone-100">
          {value === null ? "—" : format(animated)}
        </span>
        {hasTrend && (
          <svg width={width} height={height} aria-hidden>
            <motion.path
              d={path}
              className={DE_EMPHASIS}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
              initial={{ pathLength: 0 }}
              animate={{ pathLength: 1 }}
              transition={{ duration: 0.6, ease: "easeOut" }}
            />
            <motion.circle
              cx={last[0]}
              cy={last[1]}
              r={3}
              className={ACCENT}
              fill="currentColor"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.6, duration: 0.2 }}
            />
          </svg>
        )}
      </div>
    </div>
  );
}
