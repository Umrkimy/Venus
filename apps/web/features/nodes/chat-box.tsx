"use client";

import { useState } from "react";

export type ChatMessage = { from: "you" | "venus"; text: string };

type ChatBoxProps = {
  deviceId: string;
  disabled: boolean;
  messages: ChatMessage[];
  onSend: (text: string) => void;
};

export default function ChatBox({
  deviceId,
  disabled,
  messages,
  onSend,
}: ChatBoxProps) {
  const [text, setText] = useState("");
  const inputId = `chat-${deviceId}`;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSend(text.trim());
    setText("");
  }

  return (
    <>
      {messages.length > 0 && (
        <ul role="log" className="mt-3 space-y-1 text-sm">
          {/* Messages are only ever added, so the position is a safe key. */}
          {messages.map((message, index) => (
            <li
              key={index}
              className={message.from === "you" ? "text-muted" : undefined}
            >
              {message.from === "you" ? "You: " : "Venus: "}
              {message.text}
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleSubmit} className="mt-3">
        <label htmlFor={inputId} className="sr-only">
          Message Venus on {deviceId}
        </label>
        <div className="flex gap-2">
          <input
            id={inputId}
            type="text"
            value={text}
            onChange={(event) => setText(event.target.value)}
            placeholder="Ask Venus anything, e.g. open spotify"
            autoComplete="off"
            className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent"
          />
          <button
            type="submit"
            disabled={disabled || text.trim() === ""}
            className="rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
          >
            Send
          </button>
        </div>
      </form>
    </>
  );
}
