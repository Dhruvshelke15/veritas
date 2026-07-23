const ACCENT = "text-[#2a78d6] dark:text-[#3987e5]";
const DE_EMPHASIS = "text-slate-300 dark:text-slate-700";

function sparklinePoints(values: number[], width: number, height: number): [number, number][] {
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const step = width / (values.length - 1);
  return values.map((v, i) => [i * step, height - ((v - min) / span) * height]);
}

export function StatTile({
  label,
  value,
  trend,
}: {
  label: string;
  value: string;
  trend?: number[];
}) {
  const width = 96;
  const height = 28;
  const hasTrend = trend && trend.length >= 2;
  const points = hasTrend ? sparklinePoints(trend!, width, height) : [];
  const path = points.map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
  const last = points[points.length - 1];

  return (
    <div className="flex flex-1 flex-col gap-2 rounded-xl border border-slate-200 px-4 py-3 dark:border-slate-800">
      <span className="text-xs font-medium uppercase tracking-wide text-slate-500 dark:text-slate-400">
        {label}
      </span>
      <div className="flex items-end justify-between gap-3">
        <span className="text-2xl font-semibold text-slate-900 dark:text-slate-100">{value}</span>
        {hasTrend && (
          <svg width={width} height={height} aria-hidden>
            <path
              d={path}
              className={DE_EMPHASIS}
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              strokeLinecap="round"
              strokeLinejoin="round"
            />
            <circle cx={last[0]} cy={last[1]} r={3} className={ACCENT} fill="currentColor" />
          </svg>
        )}
      </div>
    </div>
  );
}
