"use client";

import dynamic from "next/dynamic";

import { useCharacterOn } from "@/features/scene/character-store";
import { useCharacterInfo, useCharacterMoves } from "@/features/scene/use-character-info";
import type { MoveInfo } from "@/features/scene/uploaded-moves";

// Loaded only when she's on: with her off, the 3D code is never downloaded.
const VenusCharacter = dynamic(() => import("@/features/scene/venus-character"), {
  ssr: false,
});

// The same empty list every time, so the scene doesn't reload moves for nothing.
const NO_MOVES: MoveInfo[] = [];

// The layer behind everything: a crimson glow, and the 3D Venus in front of it.
export default function SceneBackground() {
  const characterOn = useCharacterOn();
  const info = useCharacterInfo();
  const own = info.data?.custom ? info.data : null;
  const moves = useCharacterMoves();

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_35%,var(--scene-from),var(--scene-to)_70%)]" />
      {/* Wait for Core's answer, so the template isn't loaded just to be swapped.
          Another model in use changes the key, which loads her again. */}
      {characterOn && !info.isPending && (
        <VenusCharacter key={own?.id ?? "template"} own={own !== null} moves={moves.data ?? NO_MOVES} />
      )}
    </div>
  );
}
