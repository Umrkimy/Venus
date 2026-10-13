"use client";

import { Briefcase, Smile, Zap } from "lucide-react";

import { cn } from "@/lib/utils";

export type Tone = "professional" | "friendly" | "short";

const TONES: { value: Tone; label: string; icon: typeof Briefcase }[] = [
  { value: "professional", label: "Professional", icon: Briefcase },
  { value: "friendly", label: "Friendly", icon: Smile },
  { value: "short", label: "Short", icon: Zap },
];

// Three tones side by side: one tap, and you can see all choices at once.
export default function TonePicker({ value, onChange }: { value: Tone; onChange: (tone: Tone) => void }) {
  return (
    <div role="radiogroup" aria-label="Tone" className="inline-flex rounded-lg border border-border bg-muted/50 p-0.5">
      {TONES.map(({ value: tone, label, icon: Icon }) => {
        const active = tone === value;
        return (
          <button
            key={tone}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(tone)}
            className={cn(
              "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors",
              "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
              active ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
            )}
          >
            <Icon className="size-3.5" aria-hidden="true" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

// A small round badge with the sender's initials, coloured by name, like mail apps.
export function SenderAvatar({ name, className }: { name: string; className?: string }) {
  const words = name.replace(/[^\p{L}\p{N} ]/gu, " ").trim().split(/\s+/).filter(Boolean);
  const initials = (words.length > 1 ? words[0][0] + words[1][0] : (words[0] ?? "?").slice(0, 2)).toUpperCase();
  let hash = 0;
  for (const char of name) hash = (hash * 31 + char.charCodeAt(0)) % 360;
  return (
    <span
      aria-hidden="true"
      className={cn("flex size-9 shrink-0 items-center justify-center rounded-full text-xs font-semibold text-white", className)}
      style={{ backgroundColor: `hsl(${hash} 45% 42%)` }}
    >
      {initials}
    </span>
  );
}
