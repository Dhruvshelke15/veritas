import { useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import type { ChatTurn } from "../hooks/useChatStream";
import { ChatMessage } from "../components/ChatMessage";
import { MessageInput } from "../components/MessageInput";

interface ChatPageProps {
  turns: ChatTurn[];
  ask: (query: string) => Promise<void>;
}

const EXAMPLES = [
  "How many days of unemployment are allowed on OPT?",
  "Who qualifies for the STEM OPT extension?",
  "What is the cap-gap extension?",
];

export function ChatPage({ turns, ask }: ChatPageProps) {
  const bottomRef = useRef<HTMLDivElement>(null);
  const isStreaming = turns.some((t) => t.status === "streaming");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-5xl flex-col px-4 sm:px-6">
      <div className="flex-1 overflow-y-auto py-8">
        {turns.length === 0 ? (
          <div className="mt-6 max-w-xl">
            <h1 className="text-2xl font-bold tracking-tight">Ask about OPT, STEM OPT, cap-gap, or H-1B</h1>
            <p className="mt-2 font-serif text-muted dark:text-muted-dark">
              Answers come only from the source documents, with the passages they rely on. Try one of these,
              or <Link to="/" className="text-form underline underline-offset-2 dark:text-form-dark">pick your stage</Link>.
            </p>
            <div className="mt-6 border-t border-rule dark:border-rule-dark">
              {EXAMPLES.map((q) => (
                <button
                  key={q}
                  type="button"
                  onClick={() => ask(q)}
                  className="block w-full border-b border-rule py-3 text-left font-serif hover:text-form dark:border-rule-dark dark:hover:text-form-dark"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="flex max-w-3xl flex-col">
            {turns.map((turn) => (
              <ChatMessage key={turn.id} turn={turn} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div className="max-w-3xl border-t border-rule bg-paper py-4 dark:border-rule-dark dark:bg-paper-dark">
        <MessageInput onSubmit={ask} disabled={isStreaming} />
      </div>
    </div>
  );
}
