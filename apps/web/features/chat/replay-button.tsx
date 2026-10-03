"use client";

import { RotateCcw } from "lucide-react";

import { Button } from "@/components/ui/button";

type ReplayButtonProps = {
  onReplay: () => void;
  // This message is playing now.
  playing: boolean;
};

// Hear a line again; shows when you point at (or tab to) the message.
export default function ReplayButton({ onReplay, playing }: ReplayButtonProps) {
  return (
    <Button
      type="button"
      size="icon"
      variant="ghost"
      onClick={onReplay}
      disabled={playing}
      aria-label="Hear this again"
      className="ml-1 size-7 align-middle opacity-0 group-hover:opacity-100 focus-visible:opacity-100 disabled:opacity-60"
    >
      <RotateCcw className={playing ? "motion-safe:animate-pulse" : undefined} />
    </Button>
  );
}
