import { motion } from "motion/react";

const BAR_FILL = "text-[#2a78d6] dark:text-[#3987e5]";
const BAR_THICKNESS = 22;
const SLOT_WIDTH = 76;
const CHART_HEIGHT = 120;

export function CategoryAccuracyBar({ accuracy }: { accuracy: Record<string, number> }) {
  const categories = Object.entries(accuracy).sort(([a], [b]) => a.localeCompare(b));
  if (categories.length === 0) {
    return <p className="text-sm text-stone-500 dark:text-stone-400">No classifier data yet.</p>;
  }

  const width = categories.length * SLOT_WIDTH;

  return (
    <div className="flex flex-col gap-2">
      <svg width={width} height={CHART_HEIGHT + 34} role="img" aria-label="Classifier accuracy by category">
        <line
          x1={0}
          y1={CHART_HEIGHT}
          x2={width}
          y2={CHART_HEIGHT}
          stroke="currentColor"
          className="text-stone-300 dark:text-stone-700"
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
                className="fill-stone-700 text-[11px] dark:fill-stone-300"
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
                className="fill-stone-500 text-[10px] dark:fill-stone-400"
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
      </svg>
    </div>
  );
}
