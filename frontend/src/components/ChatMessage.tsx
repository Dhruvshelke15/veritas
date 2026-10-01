import clsx from "clsx";
import type { ChatTurn } from "../hooks/useChatStream";
import { CitationsPanel } from "./CitationsPanel";

type Stamp = { text: string; tone: "verified" | "refusal" | "pending" };

// One small stamp per answer says how far to trust it, before anyone reads the text.
function stampFor(turn: ChatTurn): Stamp | null {
  if (turn.status === "streaming") return { text: "Reading the documents", tone: "pending" };
  if (turn.status === "error") return null;
  if (turn.routingAction === "reject") return { text: "Outside what Veritas covers", tone: "refusal" };
  const final = turn.final;
  if (!final) return null;
  if (final.citations.length > 0) {
    const n = final.citations.length;
    return { text: `Checked against ${n} ${n === 1 ? "source" : "sources"}`, tone: "verified" };
  }
  if (!final.sufficient_context) return { text: "Not in the documents", tone: "refusal" };
  return null;
}

export function ChatMessage({ turn }: { turn: ChatTurn }) {
  const stamp = stampFor(turn);

  return (
    <article className="border-b border-rule py-8 first:pt-0 last:border-0 dark:border-rule-dark">
      <h2 className="text-lg font-semibold leading-snug">{turn.query}</h2>

      {stamp && (
        <p
          className={clsx(
            "mt-2 inline-block rounded-sm border px-2 py-0.5 text-xs font-semibold",
            stamp.tone === "verified" && "border-verified text-verified dark:border-verified-dark dark:text-verified-dark",
            stamp.tone === "refusal" && "border-refusal text-refusal dark:border-refusal-dark dark:text-refusal-dark",
            stamp.tone === "pending" && "border-rule text-muted dark:border-rule-dark dark:text-muted-dark",
          )}
        >
          {stamp.text}
        </p>
      )}

      {turn.routingAction === "advise" && (
        <p className="mt-3 text-sm text-muted dark:text-muted-dark">
          This asks for advice. Veritas sticks to what the documents say, so confirm any decision with your DSO.
        </p>
      )}

      <p className="mt-4 max-w-[68ch] whitespace-pre-wrap font-serif text-[1.0625rem] leading-[1.7]">
        {turn.displayedText}
        {turn.status === "streaming" && (
          <span className="ml-0.5 inline-block h-4 w-1.5 translate-y-0.5 animate-pulse bg-form dark:bg-form-dark" aria-hidden />
        )}
      </p>

      {turn.status === "error" && (
        <p className="mt-3 text-sm text-refusal dark:text-refusal-dark">
          Couldn't get an answer: {turn.error}. Check that the backend is running, then ask again.
        </p>
      )}

      {turn.reconciled && (
        <p className="mt-3 text-sm text-muted dark:text-muted-dark">
          Updated after the citation check, so this may differ from what appeared while it was writing.
        </p>
      )}

      {turn.final && <CitationsPanel citations={turn.final.citations} />}
    </article>
  );
}
