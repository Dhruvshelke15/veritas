import { motion } from "motion/react";

const BAR_FILL = "text-form dark:text-form-dark";
const BAR_THICKNESS = 22;
const SLOT_WIDTH = 76;
const CHART_HEIGHT = 120;
const TOP_PAD = 18; // room for the value label above a 100% bar

export function CategoryAccuracyBar({ accuracy }: { accuracy: Record<string, number> }) {
  const categories = Object.entries(accuracy).sort(([a], [b]) => a.localeCompare(b));
  if (categories.length === 0) {
    return <p className="text-sm text-muted dark:text-muted-dark">No classifier data yet.</p>;
  }

  const width = categories.length * SLOT_WIDTH;

  return (
    <div className="flex flex-col gap-2">
      <svg width={width} height={CHART_HEIGHT + TOP_PAD + 34} role="img" aria-label="Question sorting accuracy by category">
        <g transform={`translate(0 ${TOP_PAD})`}>
        <line
          x1={0}
          y1={CHART_HEIGHT}
          x2={width}
          y2={CHART_HEIGHT}
          stroke="currentColor"
          className="text-rule dark:text-rule-dark"
          strokeWidth={1}
        />
        {categories.map(([category, value], i) => {
          const barHeight = Math.max(2, value * CHART_HEIGHT);
          const slotCenter = i * SLOT_WIDTH + SLOT_WIDTH / 2;
          const x = slotCenter - BAR_THICKNESS / 2;
          const y = CHART_HEIGHT - barHeight;
          const words = category.split("_");
          const labelLines =
            words.length <= 2 ? words : [words[0], words.slice(1).join(" ")];
          return (
            <g key={category}>
              <title>{`${category}: ${(value * 100).toFixed(0)}%`}</title>
              <motion.rect
                x={x}
                width={BAR_THICKNESS}
                rx={4}
                className={BAR_FILL}
                fill="currentColor"
                initial={{ y: CHART_HEIGHT, height: 0 }}
                animate={{ y, height: barHeight }}
                transition={{ duration: 0.5, delay: i * 0.06, ease: "easeOut" }}
              />
              <motion.text
                x={slotCenter}
                y={y - 6}
                textAnchor="middle"
                className="fill-ink text-[11px] dark:fill-ink-dark"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.06 + 0.4, duration: 0.2 }}
              >
                {(value * 100).toFixed(0)}%
              </motion.text>
              <text
                x={slotCenter}
                y={CHART_HEIGHT + 14}
                textAnchor="middle"
                className="fill-muted text-[10px] dark:fill-muted-dark"
              >
                {labelLines.map((line, li) => (
                  <tspan key={li} x={slotCenter} dy={li === 0 ? 0 : 12}>
                    {line}
                  </tspan>
                ))}
              </text>
            </g>
          );
        })}
        </g>
      </svg>
    </div>
  );
}
