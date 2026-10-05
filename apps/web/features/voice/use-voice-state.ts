"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";

import { getJson } from "@/lib/get-json";
import { VOICE_POLL_MS } from "@/lib/poll";

import { isListeningActive } from "./listen-store";

export type VoiceStateName = "idle" | "listening" | "thinking" | "speaking" | "sleeping";

export type VoiceState = {
  state: VoiceStateName;
  subtitle: string;
  muted: boolean;
  // False: no "Hey Venus" loop running on the PC.
  online: boolean;
  // The chat voice turns go into (null before the first one).
  conversation_id: string | null;
};

const KEY = ["voice-state"];

function isFront(): boolean {
  return document.visibilityState === "visible" && document.hasFocus();
}

// True while this tab is the one you're looking at: shown and focused.
// Clicking into a game or another app makes it false again.
export function useFrontTab(): boolean {
  const [front, setFront] = useState(false);
  useEffect(() => {
    const update = () => setFront(isFront());
    update();
    window.addEventListener("focus", update);
    window.addEventListener("blur", update);
    document.addEventListener("visibilitychange", update);
    return () => {
      window.removeEventListener("focus", update);
      window.removeEventListener("blur", update);
      document.removeEventListener("visibilitychange", update);
    };
  }, []);
  return front;
}

// What the PC's voice loop is doing. Asking also tells Core this tab is
// watching, which fades the desktop orb out; stop asking and it comes back.
// Every orb on the page shares this one poll (same query key).
export function useVoiceState(front: boolean): VoiceState | undefined {
  const query = useQuery({
    queryKey: KEY,
    // listening=true: the browser mic is open here, so the PC pauses "Hey Venus".
    queryFn: () => getJson<VoiceState>(`/api/voice/state?listening=${isListeningActive()}`),
    enabled: front,
    refetchInterval: VOICE_POLL_MS,
    // A failed poll (Core restarting) just waits for the next one.
    retry: false,
  });
  return front ? query.data : undefined;
}

// Stops Luna on the PC (her voice, or an answer that hasn't started).
export function useStopVoice() {
  return useMutation({
    mutationFn: async () => {
      const response = await fetch("/api/voice/stop", { method: "POST" });
      if (!response.ok) throw new Error(`Request failed: ${response.status}`);
    },
  });
}
