"use client";

import { ArrowUp } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { fadeUp, springSoft, staggerDelay } from "@/lib/motion";
import ActionCard, { type ChatAction } from "./action-card";
import MicButton from "./mic-button";
import { useReadingSettings } from "./reading-settings";
import ReplayButton from "./replay-button";
import SpeakerButton from "./speaker-button";
import TypedText from "./typed-text";
import { useRecorder } from "./use-recorder";
import type { Speaking, useSpeaker } from "./use-speaker";

export type ChatMessage = {
  from: "you" | "venus";
  text: string;
  actions?: ChatAction[];
  // Sent in this visit (not loaded from a saved chat).
  live?: boolean;
  // A new Luna reply: its words come out with her voice, or at your text speed.
  reveal?: "voice" | "type";
};

// How many letters of this message Luna has said; null when she isn't typing it.
function lettersSaid(speaking: Speaking | null, id: number): number | null {
  if (!speaking || speaking.id !== id || !speaking.typing) return null;
  const before = speaking.lines.slice(0, speaking.line).join("").length;
  return before + Math.round(speaking.lines[speaking.line].length * speaking.fraction);
}

type ChatBoxProps = {
  disabled: boolean;
  placeholder: string;
  messages: ChatMessage[];
  onSend: (text: string) => void;
  // Luna's voice toggle sits next to the mic.
  speaker: ReturnType<typeof useSpeaker>;
  // Shown instead of the greeting before the first message.
  emptyState?: ReactNode;
  // Luna is working on a reply (asked here or by voice on the PC).
  thinking?: boolean;
};

function ThinkingLine() {
  return (
    <motion.li {...fadeUp} transition={springSoft} role="status" className="flex items-center gap-2 text-sm text-foreground/70">
      <span>Luna is thinking</span>
      <span aria-hidden="true" className="flex gap-1">
        {[0, 150, 300].map((delay) => (
          <span
            key={delay}
            className="size-1.5 rounded-full bg-foreground/60 motion-safe:animate-bounce"
            style={{ animationDelay: `${delay}ms` }}
          />
        ))}
      </span>
    </motion.li>
  );
}

export default function ChatBox({
  disabled,
  placeholder,
  messages,
  onSend,
  speaker,
  emptyState,
  thinking = false,
}: ChatBoxProps) {
  const [text, setText] = useState("");
  const endRef = useRef<HTMLLIElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const reading = useReadingSettings();
  // What you said goes into the box; you check it and press Enter.
  const recorder = useRecorder((heard) => {
    setText((current) => (current.trim() ? `${current.trim()} ${heard}` : heard));
    inputRef.current?.focus();
  });

  // Keep the newest line in view, like any chat app (also as Luna's lines come out).
  const speakingLine = speaker.speaking?.line;
  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [messages.length, speakingLine, thinking]);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSend(text.trim());
    setText("");
  }

  return (
    <>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-4">
          {messages.length === 0 ? (
            (emptyState ?? (
              <p className="mt-16 text-center text-3xl font-semibold tracking-tight text-balance">
                What can I do for you?
              </p>
            ))
          ) : (
            <ul role="log" className="space-y-5">
              {/* Messages are only ever added, so the position is a safe key. */}
              {messages.map((message, index) => (
                <motion.li
                  key={index}
                  {...fadeUp}
                  transition={{
                    ...springSoft,
                    delay: message.live ? 0 : staggerDelay(index),
                  }}
                  className={
                    message.from === "you"
                      ? "ml-auto w-fit max-w-[85%] rounded-2xl bg-foreground/10 px-4 py-2 break-words whitespace-pre-wrap"
                      : "group max-w-[85%] break-words whitespace-pre-wrap drop-shadow-sm"
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
                  {message.reveal ? (
                    <TypedText
                      text={message.text}
                      reveal={message.reveal}
                      said={lettersSaid(speaker.speaking, index)}
                      speed={reading.textSpeed}
                      instant={reading.instantText}
                    />
                  ) : (
                    message.text
                  )}
                  {message.from === "venus" && message.text && (
                    <ReplayButton
                      onReplay={() => speaker.replay(index, message.text)}
                      playing={speaker.speaking?.id === index}
                    />
                  )}
                </motion.li>
              ))}
              {thinking && <ThinkingLine />}
              <li ref={endRef} aria-hidden="true" />
            </ul>
          )}
        </div>
      </div>
      <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl px-4 pb-3">
        <label htmlFor="chat-input" className="sr-only">
          Message Venus
        </label>
        {/* Frosted pill: readable over the scene while it still shows through. */}
        <div className="flex items-end gap-2 rounded-3xl border border-input bg-background/40 py-2 pr-2 pl-3 shadow-lg backdrop-blur-md focus-within:ring-2 focus-within:ring-ring">
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
            className="rounded-full"
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
        <p className="mt-2 text-center text-xs text-muted-foreground">
          Venus can make mistakes.
        </p>
      </form>
    </>
  );
}
