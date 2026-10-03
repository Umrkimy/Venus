"use client";

import { Volume2, VolumeX } from "lucide-react";

import { Button } from "@/components/ui/button";

import type { useSpeaker } from "./use-speaker";

type SpeakerButtonProps = {
  speaker: ReturnType<typeof useSpeaker>;
};

// On: Luna says her replies out loud. Off: text only, no voice credit used.
export default function SpeakerButton({ speaker }: SpeakerButtonProps) {
  const { on, playing, toggle } = speaker;

  return (
    <Button
      type="button"
      size="icon"
      variant="ghost"
      onClick={toggle}
      aria-pressed={on}
      aria-label={on ? "Venus speaks replies" : "Venus replies in text only"}
      className={playing ? "motion-safe:animate-pulse" : undefined}
    >
      {on ? <Volume2 /> : <VolumeX className="text-muted-foreground" />}
    </Button>
  );
}
