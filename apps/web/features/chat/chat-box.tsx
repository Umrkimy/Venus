"use client";

import { ArrowUp, Focus } from "lucide-react";
import { motion } from "motion/react";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { type Mood, setMood } from "@/features/scene/scene-mood";
import { setStage, useResetView } from "@/features/scene/stage-store";
import MuteButton from "@/features/voice/mute-button";
import type { VoiceStateName } from "@/features/voice/use-voice-state";
import VoiceOrb from "@/features/voice/voice-orb";
import { fadeUp, springSoft } from "@/lib/motion";
import type { ChatAction } from "./action-card";
import ChatLog from "./chat-log";
import DialogBox, { Dots } from "./dialog-box";
import SpeakerButton from "./speaker-button";
import type { useSpeaker } from "./use-speaker";

export type ChatMessage = {
  from: "you" | "venus";
  text: string;
  actions?: ChatAction[];
  // Sent in this visit (not loaded from a saved chat).
  live?: boolean;
  // A new Luna reply: its words come out with her voice, or at your text speed.
  reveal?: "voice" | "type";
};

export type Speaker = ReturnType<typeof useSpeaker>;

type ChatBoxProps = {
  disabled: boolean;
  placeholder: string;
  messages: ChatMessage[];
  onSend: (text: string) => void;
  // Luna's voice toggle sits next to the mute button.
  speaker: Speaker;
  // Shown on the stage before the first message (a project's chat list).
  emptyState?: ReactNode;
  // A small card in the stage's top-left before the first message; Venus stays in view.
  corner?: ReactNode;
  // Luna is working on a reply (asked here or by voice on the PC).
  thinking?: boolean;
  // You're talking to Venus right now; your words land here next.
  listening?: boolean;
  // What you've said so far, shown live (browser speech only).
  liveWords?: string;
  // Hands-free in this tab (null when off), and how to stop its turn.
  localVoice?: VoiceStateName | null;
  onStopVoice?: () => void;
  // Which PC runs your commands (shows only with two or more online).
  pcPicker?: ReactNode;
  // Things to try, as buttons above the input (the portfolio demo).
  suggestions?: string[];
};

// The camera listens for drags on the whole stage and grabs the pointer on
// press, which swallowed clicks on the buttons there now and then. Its listener
// is a plain DOM one, so React's onPointerDown would come too late: stop it here.
function keepFromCamera(element: HTMLElement | null) {
  if (!element) return;
  const stop = (event: PointerEvent) => event.stopPropagation();
  element.addEventListener("pointerdown", stop);
  return () => element.removeEventListener("pointerdown", stop);
}

export default function ChatBox({
  disabled,
  placeholder,
  messages,
  onSend,
  speaker,
  emptyState,
  corner,
  thinking = false,
  listening = false,
  liveWords = "",
  localVoice = null,
  onStopVoice = () => {},
  pcPicker,
  suggestions,
}: ChatBoxProps) {
  const [text, setText] = useState("");
  const lineRef = useRef<HTMLDivElement>(null);

  // Her newest line, and yours if she hasn't answered it yet.
  const herIndex = messages.findLastIndex((message) => message.from === "venus");
  const her = herIndex >= 0 ? messages[herIndex] : null;
  const yourIndex = messages.findLastIndex((message) => message.from === "you");
  const yours = yourIndex > herIndex ? messages[yourIndex] : null;
  const hearing = listening || liveWords !== "";
  const empty = messages.length === 0 && !hearing && !thinking;
  // A project's chat list fills the stage: then it scrolls instead of moving the camera.
  const listOnStage = empty && emptyState !== undefined;
  const resetView = useResetView();

  // Venus's body shows what's going on: talking, thinking, or listening to you.
  const mood: Mood = speaker.speaking
    ? "talking"
    : thinking
      ? "thinking"
      : hearing || text !== ""
        ? "listening"
        : "idle";
  useEffect(() => setMood(mood), [mood]);
  useEffect(() => () => setMood("idle"), []);

  const stageRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    setStage(listOnStage ? null : stageRef.current);
    return () => setStage(null);
  }, [listOnStage]);

  // A long reply scrolls inside the box; keep the words being said in view.
  const speakingLine = speaker.speaking?.line;
  useEffect(() => {
    const box = lineRef.current;
    if (box) box.scrollTop = box.scrollHeight;
  }, [herIndex, speakingLine]);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSend(text.trim());
    setText("");
  }

  return (
    <>
      {/* The stage: open space so Venus shows, with the orb at its bottom. */}
      <div
        ref={stageRef}
        className={`relative flex min-h-0 flex-1 flex-col ${resetView && !listOnStage ? "cursor-grab active:cursor-grabbing" : ""}`}
      >
        <div
          ref={keepFromCamera}
          className="pointer-events-none absolute top-0 right-4 z-10 flex gap-2"
        >
          {resetView && !listOnStage && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={resetView}
              title="Reset view (or double-click)"
              className="pointer-events-auto rounded-full bg-background/50 backdrop-blur-md"
            >
              <Focus />
              Reset view
            </Button>
          )}
          <ChatLog messages={messages} speaker={speaker} />
        </div>
        {empty && corner && !listOnStage && (
          <div ref={keepFromCamera} className="absolute top-12 left-4 z-10 max-w-[calc(100%-2rem)] sm:top-0 sm:max-w-xs">
            {corner}
          </div>
        )}
        {listOnStage && (
          <div className="min-h-0 flex-1 overflow-y-auto">
            <div className="mx-auto w-full max-w-3xl px-4 pt-12 pb-8">{emptyState}</div>
          </div>
        )}
        <div className="pointer-events-none absolute inset-x-0 bottom-0">
          <VoiceOrb local={localVoice} onStopLocal={onStopVoice} />
        </div>
      </div>

      <div className="mx-auto w-full max-w-3xl px-4">
        {/* Your side: your words as you say them, or the line she's answering. */}
        {(hearing || yours) && (
          <motion.p
            key={hearing ? "live" : yourIndex}
            {...fadeUp}
            transition={springSoft}
            role={hearing ? "status" : undefined}
            className="mb-4 ml-auto flex w-fit max-w-[85%] items-center gap-2 rounded-2xl bg-background/40 px-4 py-1.5 text-sm break-words whitespace-pre-wrap text-foreground/80 backdrop-blur-md"
          >
            <span className="sr-only">You: </span>
            {liveWords ||
              (listening ? (
                <>
                  Listening <Dots />
                </>
              ) : (
                yours?.text
              ))}
          </motion.p>
        )}

        <DialogBox her={her} herIndex={herIndex} thinking={thinking} speaker={speaker} lineRef={lineRef} />
      </div>

      <form onSubmit={handleSubmit} className="mx-auto w-full max-w-3xl px-4 pt-3 pb-3">
        {suggestions && suggestions.length > 0 && (
          <div className="mb-2 flex gap-2 overflow-x-auto [scrollbar-width:none]" aria-label="Things to try">
            {suggestions.map((suggestion) => (
              <button
                key={suggestion}
                type="button"
                disabled={disabled}
                onClick={() => onSend(suggestion)}
                className="shrink-0 rounded-full border border-input bg-background/40 px-3 py-1 text-sm text-foreground/80 backdrop-blur-md hover:bg-background/60 hover:text-foreground disabled:opacity-50"
              >
                {suggestion}
              </button>
            ))}
          </div>
        )}
        <label htmlFor="chat-input" className="sr-only">
          Message Venus
        </label>
        {/* Frosted pill: readable over the scene while it still shows through. */}
        <div className="flex items-end gap-2 rounded-3xl border border-input bg-background/40 py-2 pr-2 pl-3 shadow-lg backdrop-blur-md focus-within:ring-2 focus-within:ring-ring">
          <textarea
            id="chat-input"
            rows={1}
            value={text}
            // Venus refuses longer messages, so stop typing there.
            maxLength={4000}
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
          {pcPicker}
          <SpeakerButton speaker={speaker} />
          <MuteButton />
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
