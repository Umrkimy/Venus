"use client";

import { motion } from "motion/react";
import type { Ref } from "react";

import { fadeUp, springSoft } from "@/lib/motion";
import ActionCard from "./action-card";
import type { ChatMessage, Speaker } from "./chat-box";
import { useReadingSettings } from "./reading-settings";
import ReplayButton from "./replay-button";
import TypedText from "./typed-text";
import type { Speaking } from "./use-speaker";

// How many letters of this message Luna has said; null when she isn't typing it.
function lettersSaid(speaking: Speaking | null, id: number): number | null {
  if (!speaking || speaking.id !== id || !speaking.typing) return null;
  const before = speaking.lines.slice(0, speaking.line).join("").length;
  return (
    before +
    Math.round(speaking.lines[speaking.line].length * speaking.fraction)
  );
}

export function Dots() {
  return (
    <span aria-hidden="true" className="flex gap-1">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 rounded-full bg-foreground/60 motion-safe:animate-bounce"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </span>
  );
}

type Props = {
  her: ChatMessage | null;
  herIndex: number;
  thinking: boolean;
  speaker: Speaker;
  // The line scrolls inside the box; the chat keeps the words being said in view.
  lineRef: Ref<HTMLDivElement>;
};

// The visual-novel box: Venus's name tag over her newest line.
export default function DialogBox({ her, herIndex, thinking, speaker, lineRef }: Props) {
  const reading = useReadingSettings();

  return (
    <div className="relative rounded-2xl border border-border/60 bg-background/55 px-5 pt-6 pb-4 shadow-lg backdrop-blur-md">
      <span className="absolute -top-3 left-4 rounded-full bg-primary px-3 py-0.5 text-sm font-semibold text-primary-foreground shadow-sm">
        Venus
      </span>
      <div
        ref={lineRef}
        aria-live="polite"
        className="group max-h-[30svh] overflow-y-auto break-words whitespace-pre-wrap"
      >
        {thinking ? (
          <p role="status" className="flex items-center gap-2 text-foreground/70">
            <span>Thinking</span>
            <Dots />
          </p>
        ) : her ? (
          <motion.div key={herIndex} {...fadeUp} transition={springSoft}>
            <span className="sr-only">Venus: </span>
            {/* What Venus did comes first, then what she says about it. */}
            {her.actions && her.actions.length > 0 && (
              <ActionCard actions={her.actions} startOpen={her.live ?? false} />
            )}
            {her.reveal ? (
              <TypedText
                text={her.text}
                reveal={her.reveal}
                said={lettersSaid(speaker.speaking, herIndex)}
                speed={reading.textSpeed}
                instant={reading.instantText}
              />
            ) : (
              her.text
            )}
            {her.text && (
              <ReplayButton
                onReplay={() => speaker.replay(herIndex, her.text)}
                playing={speaker.speaking?.id === herIndex}
              />
            )}
          </motion.div>
        ) : (
          <p>What can I do for you?</p>
        )}
      </div>
    </div>
  );
}
