"use client";

import { ArrowUp } from "lucide-react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import ActionCard, { type ChatAction } from "./action-card";
import MicButton from "./mic-button";
import SpeakerButton from "./speaker-button";
import { useRecorder } from "./use-recorder";
import type { useSpeaker } from "./use-speaker";

export type ChatMessage = {
  from: "you" | "venus";
  text: string;
  actions?: ChatAction[];
  // Sent in this visit (not loaded from a saved chat).
  live?: boolean;
};

type ChatBoxProps = {
  disabled: boolean;
  placeholder: string;
  messages: ChatMessage[];
  onSend: (text: string) => void;
  // Luna's voice toggle sits next to the mic.
  speaker: ReturnType<typeof useSpeaker>;
  // Shown instead of the greeting before the first message.
  emptyState?: ReactNode;
};

export default function ChatBox({
  disabled,
  placeholder,
  messages,
  onSend,
  speaker,
  emptyState,
}: ChatBoxProps) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLLIElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  // What you said goes into the box; you check it and press Enter.
  const recorder = useRecorder((heard) => {
    setText((current) => (current.trim() ? `${current.trim()} ${heard}` : heard));
    inputRef.current?.focus();
  });

  // Keep the newest line in view, like any chat app.
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length]);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSend(text.trim());
    setText("");
  }

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {messages.length === 0 ? (
          (emptyState ?? (
            <p className="mt-16 text-center text-3xl font-semibold tracking-tight text-balance">
              What can I do for you?
            </p>
          ))
        ) : (
          <ul role="log" className="space-y-3">
            {/* Messages are only ever added, so the position is a safe key. */}
            {messages.map((message, index) => (
              <li
                key={index}
                className={
                  message.from === "you"
                    ? "ml-auto w-fit max-w-[85%] rounded-2xl bg-foreground/10 px-4 py-2 break-words whitespace-pre-wrap"
                    : "max-w-[85%] break-words whitespace-pre-wrap"
                }
              >
                <span className="sr-only">
                  {message.from === "you" ? "You: " : "Venus: "}
                </span>
                {/* What Venus did comes first, then what she says about it. */}
                {message.actions && message.actions.length > 0 && (
                  <ActionCard
                    actions={message.actions}
                    startOpen={message.live ?? false}
                  />
                )}
                {message.text}
              </li>
            ))}
            <li ref={endRef} aria-hidden="true" />
          </ul>
        )}
      </div>
      <form onSubmit={handleSubmit} className="p-3">
        <label htmlFor="chat-input" className="sr-only">
          Message Venus
        </label>
        <div className="flex items-end gap-2 rounded-xl border border-input bg-background/60 p-2 focus-within:ring-2 focus-within:ring-ring">
          <textarea
            ref={inputRef}
            id="chat-input"
            rows={1}
            value={text}
            onChange={(event) => setText(event.target.value)}
            onKeyDown={(event) => {
              // Enter sends, Shift+Enter makes a new line.
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault();
                event.currentTarget.form?.requestSubmit();
              }
            }}
            placeholder={placeholder}
            autoComplete="off"
            className="max-h-40 min-h-9 flex-1 resize-none bg-transparent px-2 py-1.5 outline-none placeholder:text-muted-foreground field-sizing-content"
          />
          <SpeakerButton speaker={speaker} />
          <MicButton recorder={recorder} disabled={disabled} />
          <Button
            type="submit"
            size="icon"
            disabled={disabled || text.trim() === ""}
            aria-label="Send"
          >
            <ArrowUp />
          </Button>
        </div>
        {recorder.error && (
          <p role="alert" className="mt-1.5 px-2 text-sm text-destructive">
            {recorder.error}
          </p>
        )}
        {speaker.error && (
          <p role="alert" className="mt-1.5 px-2 text-sm text-destructive">
            {speaker.error}
          </p>
        )}
      </form>
    </>
  );
}
