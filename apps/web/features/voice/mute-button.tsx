"use client";

import { Mic, MicOff } from "lucide-react";

import { Button } from "@/components/ui/button";

import { setListenOn, useListenOn } from "./listen-store";

// Hands-free on or off: on, the browser mic listens all the time while this
// tab is in front (no "Hey Venus"), like ChatGPT's voice mode.
export default function MuteButton() {
  const on = useListenOn();
  const label = on ? "Mute: stop listening" : "Unmute: talk to Venus hands-free";

  return (
    <Button
      type="button"
      size="icon"
      variant="ghost"
      onClick={() => setListenOn(!on)}
      aria-pressed={on}
      aria-label={label}
      title={label}
    >
      {on ? <Mic /> : <MicOff className="text-muted-foreground" />}
    </Button>
  );
}
