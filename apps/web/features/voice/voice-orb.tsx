"use client";

import { Square } from "lucide-react";
import { AnimatePresence, motion } from "motion/react";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";

import { springSoft } from "@/lib/motion";

import { setListenOn, useListenOn } from "./listen-store";
import Orb from "./orb";
import { useFrontTab, useStopVoice, useVoiceState, type VoiceStateName } from "./use-voice-state";

const SAY: Record<string, string> = {
  listening: "Venus is listening",
  thinking: "Venus is thinking",
  speaking: "Venus is speaking",
  sleeping: "Venus is going to sleep",
};

// When a voice turn on the PC starts (or moves to a new chat), open that chat,
// so you see your words and Luna's answer without hunting for it in the sidebar.
// Once per turn: if you click away mid-turn, it doesn't pull you back.
function useFollowVoiceChat(state: string | undefined, conversationId: string | null) {
  const router = useRouter();
  const pathname = usePathname();
  const followed = useRef<string | null>(null);
  const active = state !== undefined && state !== "idle";

  useEffect(() => {
    if (!active) {
      followed.current = null;
      return;
    }
    if (!conversationId || followed.current === conversationId) return;
    followed.current = conversationId;
    const target = `/chat/${conversationId}`;
    if (pathname !== target) router.push(target);
  }, [active, conversationId, pathname, router]);
}

type VoiceOrbProps = {
  // Hands-free in this tab: what the browser's own voice turn is doing.
  // null: hands-free is off, so the orb follows "Hey Venus" on the PC.
  local: VoiceStateName | null;
  // Stops this tab's own turn (her voice here, or the answer on its way).
  onStopLocal: () => void;
};

// Venus's orb, always in the middle above the chat box, like ChatGPT's voice
// mode: calm between turns, moving while you and Luna talk (the 3D Venus
// joins it later). Luna's line floats above it while she speaks on the PC.
// Click it while she thinks or talks to stop her; otherwise it turns
// hands-free listening on or off (same as the mic button).
export default function VoiceOrb({ local, onStopLocal }: VoiceOrbProps) {
  const voice = useVoiceState(useFrontTab());
  const stopPc = useStopVoice();
  const listenOn = useListenOn();
  useFollowVoiceChat(voice?.state, voice?.conversation_id ?? null);

  const pcState = voice?.state ?? "idle";
  const pcBusy = pcState === "thinking" || pcState === "speaking";
  const state = local !== null && local !== "idle" ? local : pcState;
  const localBusy = local === "thinking" || local === "speaking";
  // Grey and slow while muted: hands-free off here and no "Hey Venus" turn
  // running on the PC (a PC turn still lights it up).
  const quiet = !listenOn && pcState === "idle";

  const busy = localBusy || pcBusy;

  function click() {
    if (!busy) {
      setListenOn(!listenOn);
      return;
    }
    if (localBusy) onStopLocal();
    if (pcBusy) stopPc.mutate();
  }

  let label = listenOn ? "Stop listening" : "Talk to Venus hands-free";
  if (busy) label = "Stop Venus";

  return (
    <div className="pointer-events-none relative flex shrink-0 justify-center py-3">
      <span role="status" className="sr-only">
        {state === "idle" ? "" : SAY[state]}
      </span>
      <AnimatePresence>
        {pcState === "speaking" && voice?.subtitle && (
          // Floats over the messages, so the chat doesn't jump when it shows.
          <motion.p
            key="subtitle"
            initial={{ opacity: 0, y: 6 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={springSoft}
            className="absolute bottom-full max-w-md rounded-xl bg-black/70 px-3 py-2 text-center text-sm text-white shadow-lg backdrop-blur-sm"
          >
            {voice.subtitle}
          </motion.p>
        )}
      </AnimatePresence>
      <button
        type="button"
        onClick={click}
        aria-label={label}
        title={label}
        className="group pointer-events-auto relative grid place-items-center rounded-full outline-none focus-visible:ring-2 focus-visible:ring-ring motion-safe:transition-transform motion-safe:active:scale-95"
      >
        <Orb state={state} quiet={quiet} size={96} />
        {busy && (
          // Shows on hover: a click here stops her.
          <Square
            aria-hidden="true"
            className="absolute size-5 fill-white text-white opacity-0 drop-shadow transition-opacity group-hover:opacity-90 group-focus-visible:opacity-90"
          />
        )}
      </button>
    </div>
  );
}
