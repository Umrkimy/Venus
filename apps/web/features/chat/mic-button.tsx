"use client";

import { Loader2, Mic, Square } from "lucide-react";

import { Button } from "@/components/ui/button";

import type { useRecorder } from "./use-recorder";

type MicButtonProps = {
  recorder: ReturnType<typeof useRecorder>;
  disabled: boolean;
};

// Click to start talking, click again to stop; the words land in the box.
export default function MicButton({ recorder, disabled }: MicButtonProps) {
  const { state, start, stop } = recorder;

  if (state === "transcribing") {
    return (
      <Button type="button" size="icon" variant="ghost" disabled aria-label="Listening back">
        <Loader2 className="motion-safe:animate-spin" />
      </Button>
    );
  }

  if (state === "recording") {
    return (
      <Button
        type="button"
        size="icon"
        variant="destructive"
        onClick={stop}
        aria-label="Stop recording"
        className="motion-safe:animate-pulse"
      >
        <Square className="fill-current" />
      </Button>
    );
  }

  return (
    <Button
      type="button"
      size="icon"
      variant="ghost"
      onClick={() => void start()}
      disabled={disabled}
      aria-label="Talk to Venus"
    >
      <Mic />
    </Button>
  );
}
