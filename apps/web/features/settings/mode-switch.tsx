"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

type Mode = "confirm" | "full";
type ModeResponse = { mode: Mode };

const OPTIONS: { value: Mode; label: string }[] = [
  { value: "confirm", label: "Confirm" },
  { value: "full", label: "Full" },
];

export default function ModeSwitch() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mode = useQuery({
    queryKey: ["mode"],
    queryFn: () => getJson<ModeResponse>("/api/settings/mode"),
  });

  async function choose(next: Mode) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/settings/mode", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: next }),
      });
      if (!response.ok) {
        setError("Couldn't change the mode.");
        return;
      }
      // Re-read from Core so the switch shows what was actually saved.
      await mode.refetch();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  if (mode.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading mode</span>
        <div className="h-8 w-36 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (mode.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the mode.
      </p>
    );
  }

  const current = mode.data.mode;

  return (
    <div>
      <div
        role="group"
        aria-label="Command mode"
        className="inline-flex rounded-lg border border-border bg-muted/50 p-1"
      >
        {OPTIONS.map((option) => {
          const active = option.value === current;
          return (
            <button
              key={option.value}
              type="button"
              aria-pressed={active}
              disabled={busy}
              onClick={() => choose(option.value)}
              className={`rounded-md px-4 py-1.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50 ${
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
        {current === "full"
          ? "Apps open without asking."
          : "You approve each command."}
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
