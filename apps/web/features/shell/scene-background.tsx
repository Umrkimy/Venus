"use client";

import dynamic from "next/dynamic";

import { useCharacterOn } from "@/features/scene/character-store";
import { useCharacterInfo } from "@/features/scene/use-character-info";

// Loaded only when she's on: with her off, the 3D code is never downloaded.
const VenusCharacter = dynamic(() => import("@/features/scene/venus-character"), {
  ssr: false,
});

// The layer behind everything: a crimson glow, and the 3D Venus in front of it.
export default function SceneBackground() {
  const characterOn = useCharacterOn();
  const info = useCharacterInfo();
  const own = info.data?.custom ? info.data : null;

  return (
    <div aria-hidden="true" className="pointer-events-none absolute inset-0">
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_50%_35%,var(--scene-from),var(--scene-to)_70%)]" />
      {/* Wait for Core's answer, so the template isn't loaded just to be swapped.
          A new upload changes the key, which loads her again. */}
      {characterOn && !info.isPending && (
        <VenusCharacter key={own?.uploaded_at ?? "template"} own={own !== null} />
      )}
    </div>
  );
}
