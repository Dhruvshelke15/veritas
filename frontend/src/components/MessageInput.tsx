import { useState } from "react";
import type { FormEvent } from "react";

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
    <form onSubmit={handleSubmit}>
      <label htmlFor="question" className="text-sm font-semibold">
        Your question
      </label>
      <div className="mt-1.5 flex gap-2">
        <input
          id="question"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="For example: Can I travel while my OPT application is pending?"
          disabled={disabled}
          className="min-w-0 flex-1 rounded-md border border-rule bg-sheet px-3 py-2.5 text-[0.9375rem] outline-none transition-colors placeholder:text-muted/70 focus:border-form disabled:opacity-60 dark:border-rule-dark dark:bg-sheet-dark dark:placeholder:text-muted-dark/70 dark:focus:border-form-dark"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-md bg-form px-5 text-sm font-semibold text-white transition-colors hover:bg-ink disabled:cursor-not-allowed disabled:bg-rule disabled:text-muted dark:bg-form-dark dark:text-paper-dark dark:hover:bg-ink-dark dark:disabled:bg-rule-dark dark:disabled:text-muted-dark"
        >
          {disabled ? "Answering" : "Ask"}
        </button>
      </div>
    </form>
  );
}
