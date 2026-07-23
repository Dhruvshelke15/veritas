import { useCallback, useState } from "react";
import { streamAsk } from "../api/client";
import type { AskResult } from "../api/types";

export interface ChatTurn {
  id: string;
  query: string;
  status: "streaming" | "done" | "error";
  displayedText: string;
  queryCategory: string | null;
  categoryConfidence: number | null;
  routingAction: string | null;
  final: AskResult | null;
  reconciled: boolean;
  error: string | null;
}

function makeId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export function useChatStream() {
  const [turns, setTurns] = useState<ChatTurn[]>([]);

  const ask = useCallback(async (query: string) => {
    const id = makeId();
    setTurns((prev) => [
      ...prev,
      {
        id,
        query,
        status: "streaming",
        displayedText: "",
        queryCategory: null,
        categoryConfidence: null,
        routingAction: null,
        final: null,
        reconciled: false,
        error: null,
      },
    ]);

    let streamedText = "";

    const update = (patch: Partial<ChatTurn>) => {
      setTurns((prev) => prev.map((t) => (t.id === id ? { ...t, ...patch } : t)));
    };

    try {
      for await (const event of streamAsk(query)) {
        if (event.type === "meta") {
          update({
            queryCategory: event.query_category,
            categoryConfidence: event.category_confidence,
            routingAction: event.routing_action,
          });
        } else if (event.type === "answer_delta") {
          streamedText += event.text;
          update({ displayedText: streamedText });
        } else if (event.type === "final") {
          const reconciled = streamedText.length > 0 && event.answer !== streamedText;
          update({
            status: "done",
            displayedText: event.answer,
            reconciled,
            final: {
              answer: event.answer,
              citations: event.citations,
              sufficient_context: event.sufficient_context,
              hallucinated_citations: event.hallucinated_citations,
              parse_failed: event.parse_failed,
              query_category: event.query_category,
              category_confidence: event.category_confidence,
              routing_action: event.routing_action,
            },
          });
        }
      }
    } catch (err) {
      update({ status: "error", error: err instanceof Error ? err.message : String(err) });
    }
  }, []);

  return { turns, ask };
}
