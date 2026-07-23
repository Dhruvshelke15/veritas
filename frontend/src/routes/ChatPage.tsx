import { useEffect, useRef } from "react";
import { Landmark } from "lucide-react";
import { useChatStream } from "../hooks/useChatStream";
import { ChatMessage } from "../components/ChatMessage";
import { MessageInput } from "../components/MessageInput";

export function ChatPage() {
  const { turns, ask } = useChatStream();
  const bottomRef = useRef<HTMLDivElement>(null);
  const isStreaming = turns.some((t) => t.status === "streaming");

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns]);

  return (
    <div className="mx-auto flex h-[calc(100vh-4rem)] max-w-3xl flex-col px-4">
      <div className="flex-1 overflow-y-auto py-6">
        {turns.length === 0 && (
          <div className="mx-auto mt-16 max-w-md text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-100 dark:bg-brand-800">
              <Landmark className="h-7 w-7 text-brand-600 dark:text-brand-300" strokeWidth={1.75} />
            </div>
            <h1 className="mt-5 font-display text-2xl font-medium text-stone-900 dark:text-stone-100">
              Ask about your F-1 work pathway
            </h1>
            <p className="mt-2 text-sm leading-relaxed text-stone-500 dark:text-stone-400">
              OPT, STEM OPT, cap-gap, and the H-1B transition. Every answer is grounded in
              official USCIS and ICE documents, with citations you can check yourself.
            </p>
          </div>
        )}
        <div className="flex flex-col gap-6">
          {turns.map((turn) => (
            <ChatMessage key={turn.id} turn={turn} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-stone-200 py-4 dark:border-stone-800">
        <MessageInput onSubmit={ask} disabled={isStreaming} />
      </div>
    </div>
  );
}
