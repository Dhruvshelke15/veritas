import type { ChatTurn } from "../hooks/useChatStream";
import { CitationsPanel } from "./CitationsPanel";

const ROUTING_LABEL: Record<string, string> = {
  reject: "Out of scope",
  advise: "Advice-seeking",
  standard: "Standard",
};

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="self-end rounded-2xl rounded-br-sm bg-slate-900 px-4 py-2 text-white dark:bg-slate-100 dark:text-slate-900">
        {turn.query}
      </div>

      <div className="self-start max-w-2xl rounded-2xl rounded-bl-sm border border-slate-200 bg-white px-4 py-3 dark:border-slate-800 dark:bg-slate-900">
        {turn.routingAction && turn.routingAction !== "standard" && (
          <span className="mb-1 inline-block rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300">
            {ROUTING_LABEL[turn.routingAction] ?? turn.routingAction}
          </span>
        )}

        <p className="whitespace-pre-wrap text-slate-800 dark:text-slate-200">
          {turn.displayedText || (turn.status === "streaming" ? "…" : "")}
        </p>

        {turn.status === "streaming" && (
          <span className="mt-1 inline-block h-4 w-1.5 animate-pulse bg-slate-400" aria-hidden />
        )}

        {turn.status === "error" && (
          <p className="mt-2 text-sm text-red-600 dark:text-red-400">Error: {turn.error}</p>
        )}

        {turn.reconciled && (
          <p className="mt-2 text-xs italic text-slate-500 dark:text-slate-400">
            Answer revised after citation verification.
          </p>
        )}

        {turn.final && !turn.final.sufficient_context && turn.final.citations.length === 0 && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400">
            The documents don't provide enough grounded information to answer confidently.
          </p>
        )}

        {turn.final && <CitationsPanel citations={turn.final.citations} />}
      </div>
    </div>
  );
}
