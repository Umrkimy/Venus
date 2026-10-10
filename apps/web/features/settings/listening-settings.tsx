"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";

import {
  END_PAUSE_KEY,
  type ListeningResponse,
} from "@/features/voice/use-end-pause";
import { getJson } from "@/lib/get-json";

import { LABEL_CLASS } from "./field-styles";

// Saved this long after you stop dragging, not on every step.
const SAVE_AFTER_MS = 400;

export default function ListeningSettings() {
  const listening = useQuery({
    queryKey: END_PAUSE_KEY,
    queryFn: () => getJson<ListeningResponse>("/api/settings/listening"),
  });

  if (listening.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading listening settings</span>
        <div className="h-8 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (listening.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the listening settings.
      </p>
    );
  }

  return <PauseSlider saved={listening.data.end_pause_ms} />;
}

function PauseSlider({ saved }: { saved: number }) {
  const queryClient = useQueryClient();
  const pauseId = useId();
  const [pauseMs, setPauseMs] = useState(saved);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (pauseMs === saved) return;
    const timer = window.setTimeout(async () => {
      try {
        const response = await fetch("/api/settings/listening", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ end_pause_ms: pauseMs }),
        });
        if (!response.ok) {
          setError("Saving the pause failed.");
          return;
        }
        setError(null);
        // Hands-free reads the same query, so the web uses it at once.
        queryClient.setQueryData(END_PAUSE_KEY, await response.json());
      } catch {
        setError("Can't reach Venus Core. Is it running?");
      }
    }, SAVE_AFTER_MS);
    return () => window.clearTimeout(timer);
  }, [pauseMs, saved, queryClient]);

  return (
    <div>
      <label htmlFor={pauseId} className={LABEL_CLASS}>
        Wait after you stop talking
        <span className="ml-2 font-normal text-muted-foreground">
          {pauseMs / 1000} s
        </span>
      </label>
      <input
        id={pauseId}
        type="range"
        min={500}
        max={3000}
        step={250}
        value={pauseMs}
        onChange={(event) => setPauseMs(Number(event.target.value))}
        className="mt-2 w-full accent-primary"
      />
      <p className="mt-1 text-sm text-muted-foreground">
        Shorter feels quicker but can cut you off mid-sentence. After
        &quot;uh&quot; or &quot;and&quot; the web waits twice as long.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
