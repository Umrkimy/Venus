"use client";

import { useEffect, useState } from "react";

type TypedTextProps = {
  text: string;
  // "voice": words follow Luna's voice. "type": words type at your text speed.
  reveal: "voice" | "type";
  // Letters Luna has said so far; null when she isn't saying this message.
  said: number | null;
  speed: number;
  instant: boolean;
};

// Luna's words come out a bit at a time, like a visual novel. Click to show them all.
export default function TypedText({ text, reveal, said, speed, instant }: TypedTextProps) {
  const [typed, setTyped] = useState(0);
  const [skipped, setSkipped] = useState(false);

  useEffect(() => {
    if (reveal !== "type" || instant || skipped) return;
    const start = performance.now();
    let frame = requestAnimationFrame(function tick(now) {
      const count = Math.floor(((now - start) / 1000) * speed);
      setTyped(count);
      if (count < text.length) frame = requestAnimationFrame(tick);
    });
    return () => cancelAnimationFrame(frame);
  }, [reveal, instant, skipped, speed, text.length]);

  let shown = text.length;
  if (!instant && !skipped) {
    // Voice: once she's done with this message (or it failed), all of it shows.
    shown = reveal === "voice" ? (said ?? text.length) : typed;
  }
  const done = shown >= text.length;

  return (
    <>
      {/* Screen readers get the whole line once, not every letter. */}
      <span className="sr-only">{text}</span>
      <span
        aria-hidden="true"
        onClick={done ? undefined : () => setSkipped(true)}
        className={done ? undefined : "cursor-pointer"}
      >
        {text.slice(0, shown)}
        {!done && <span className="motion-safe:animate-pulse">▍</span>}
      </span>
    </>
  );
}
