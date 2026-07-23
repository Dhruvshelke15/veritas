import { AlertTriangle, RotateCcw, ShieldAlert, Sparkles } from "lucide-react";
import { motion } from "motion/react";
import type { ChatTurn } from "../hooks/useChatStream";
import { CitationsPanel } from "./CitationsPanel";

const ROUTING_META: Record<string, { label: string; icon: typeof ShieldAlert }> = {
  reject: { label: "Out of scope", icon: ShieldAlert },
  advise: { label: "Advice-seeking", icon: Sparkles },
};

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  const routing = turn.routingAction ? ROUTING_META[turn.routingAction] : undefined;

  return (
    <div className="flex flex-col gap-3">
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="self-end rounded-2xl rounded-br-md bg-brand-700 px-4 py-2.5 text-white shadow-sm dark:bg-brand-600"
      >
        {turn.query}
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, delay: 0.08, ease: "easeOut" }}
        className="max-w-2xl self-start rounded-2xl rounded-bl-md border border-stone-200 bg-white px-4 py-3.5 shadow-sm dark:border-stone-800 dark:bg-stone-900"
      >
        {routing && (
          <span className="mb-2 inline-flex items-center gap-1.5 rounded-full bg-accent-500/15 px-2.5 py-1 text-xs font-medium text-accent-600 dark:text-accent-400">
            <routing.icon className="h-3.5 w-3.5" strokeWidth={2} />
            {routing.label}
          </span>
        )}

        <p className="whitespace-pre-wrap leading-relaxed text-stone-800 dark:text-stone-200">
          {turn.displayedText}
          {turn.status === "streaming" && (
            <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-accent-500" aria-hidden />
          )}
        </p>

        {turn.status === "error" && (
          <p className="mt-2 flex items-center gap-1.5 text-sm text-red-600 dark:text-red-400">
            <AlertTriangle className="h-4 w-4" strokeWidth={2} />
            Error: {turn.error}
          </p>
        )}

        {turn.reconciled && (
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-2.5 flex items-center gap-1.5 text-xs italic text-stone-500 dark:text-stone-400"
          >
            <RotateCcw className="h-3.5 w-3.5 shrink-0" strokeWidth={2} />
            Answer revised after citation verification.
          </motion.p>
        )}

        {turn.final && !turn.final.sufficient_context && turn.final.citations.length === 0 && (
          <p className="mt-2.5 text-xs text-stone-500 dark:text-stone-400">
            The documents don't provide enough grounded information to answer confidently.
          </p>
        )}

        {turn.final && <CitationsPanel citations={turn.final.citations} />}
      </motion.div>
    </div>
  );
}
