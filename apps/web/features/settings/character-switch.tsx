"use client";

import { setCharacterOn, useCharacterOn } from "@/features/scene/character-store";

const OPTIONS = [
  { value: true, label: "On" },
  { value: false, label: "Off" },
];

export default function CharacterSwitch() {
  const on = useCharacterOn();

  return (
    <div>
      <div
        role="group"
        aria-label="3D character"
        className="inline-flex rounded-lg border border-border bg-muted/50 p-1"
      >
        {OPTIONS.map((option) => {
          const active = option.value === on;
          return (
            <button
              key={option.label}
              type="button"
              aria-pressed={active}
              onClick={() => setCharacterOn(option.value)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring ${
                active
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:bg-background hover:text-foreground"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        {on
          ? "Venus stands behind the chat. Turn off to save memory on this device."
          : "Plain background. Lightest on memory."}
      </p>
    </div>
  );
}
