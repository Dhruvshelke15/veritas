import { useEffect, useRef } from "react";
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
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] max-w-3xl flex-col px-4">
      <div className="flex-1 overflow-y-auto py-6">
        {turns.length === 0 && (
          <div className="mt-16 text-center text-sm text-slate-500 dark:text-slate-400">
            Ask a question about OPT, STEM OPT, cap-gap, or the H-1B transition. Answers are
            grounded in official USCIS and ICE documents, with citations.
          </div>
        )}
        <div className="flex flex-col gap-6">
          {turns.map((turn) => (
            <ChatMessage key={turn.id} turn={turn} />
          ))}
        </div>
        <div ref={bottomRef} />
      </div>
      <div className="border-t border-slate-200 py-4 dark:border-slate-800">
        <MessageInput onSubmit={ask} disabled={isStreaming} />
      </div>
    </div>
  );
}
