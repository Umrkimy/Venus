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
      <div role="status" className="mt-4">
        <span className="sr-only">Loading mode</span>
        <div className="h-8 w-36 rounded-md bg-muted/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (mode.isError) {
    return (
      <p role="alert" className="mt-4 text-sm text-danger">
        Can&apos;t load the mode.
      </p>
    );
  }

  const current = mode.data.mode;

  return (
    <div className="mt-4">
      <div
        role="group"
        aria-label="Command mode"
        className="inline-flex rounded-md border border-border p-0.5"
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
              className={`rounded px-3 py-1 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 ${
                active ? "bg-accent text-accent-foreground" : "text-muted"
              }`}
            >
              {option.label}
            </button>
          );
        })}
      </div>
      <p className="mt-1 text-xs text-muted">
        {current === "full"
          ? "Apps open without asking."
          : "You approve each command."}
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </div>
  );
}
