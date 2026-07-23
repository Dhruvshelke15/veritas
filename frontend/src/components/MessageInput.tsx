import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowUp } from "lucide-react";
import { motion } from "motion/react";

export function MessageInput({ onSubmit, disabled }: { onSubmit: (query: string) => void; disabled: boolean }) {
  const [value, setValue] = useState("");

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSubmit(trimmed);
    setValue("");
  };

  return (
    <form onSubmit={handleSubmit} className="flex items-center gap-2 rounded-2xl border border-stone-200 bg-white p-1.5 pl-4 shadow-sm transition-shadow focus-within:border-brand-400 focus-within:shadow-md dark:border-stone-800 dark:bg-stone-900 dark:focus-within:border-brand-500">
      <input
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Ask about OPT, STEM OPT, cap-gap, or the H-1B transition…"
        disabled={disabled}
        className="flex-1 bg-transparent py-2 text-sm text-stone-800 outline-none placeholder:text-stone-400 disabled:opacity-60 dark:text-stone-100 dark:placeholder:text-stone-500"
      />
      <motion.button
        whileTap={{ scale: 0.9 }}
        type="submit"
        disabled={disabled || !value.trim()}
        aria-label="Ask"
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-brand-700 text-white transition-colors hover:bg-brand-600 disabled:bg-stone-300 disabled:text-stone-400 dark:bg-brand-600 dark:hover:bg-brand-500 dark:disabled:bg-stone-700 dark:disabled:text-stone-500"
      >
        <ArrowUp className="h-4 w-4" strokeWidth={2.25} />
      </motion.button>
    </form>
  );
}
