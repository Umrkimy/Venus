"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  END_PAUSE_KEY,
  type ListeningResponse,
} from "@/features/voice/use-end-pause";
import { getJson } from "@/lib/get-json";

import { LABEL_CLASS, SELECT_TRIGGER_CLASS } from "./field-styles";

// Saved this long after you stop dragging, not on every step.
const SAVE_AFTER_MS = 400;
// A Select item can't have "" as its value, so the Windows default gets a name.
const WINDOWS_DEFAULT = "windows-default";

async function saveListening(
  body: Partial<ListeningResponse>,
): Promise<ListeningResponse | string> {
  try {
    const response = await fetch("/api/settings/listening", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok) return "Saving failed.";
    return await response.json();
  } catch {
    return "Can't reach Venus Core. Is it running?";
  }
}

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

  return (
    <div className="space-y-5">
      <PauseSlider saved={listening.data.end_pause_ms} />
      <MicPicker saved={listening.data.mic} />
    </div>
  );
}

function PauseSlider({ saved }: { saved: number }) {
  const queryClient = useQueryClient();
  const pauseId = useId();
  const [pauseMs, setPauseMs] = useState(saved);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (pauseMs === saved) return;
    const timer = window.setTimeout(async () => {
      const saved = await saveListening({ end_pause_ms: pauseMs });
      if (typeof saved === "string") {
        setError(saved);
        return;
      }
      setError(null);
      // Hands-free reads the same query, so the web uses it at once.
      queryClient.setQueryData(END_PAUSE_KEY, saved);
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

function MicPicker({ saved }: { saved: string }) {
  const queryClient = useQueryClient();
  const micId = useId();
  const [error, setError] = useState<string | null>(null);
  // The PC sends its mics to Core while Venus runs there.
  const mics = useQuery({
    queryKey: ["voice-mics"],
    queryFn: () => getJson<{ mics: string[] }>("/api/voice/mics"),
  });
  const names = mics.data?.mics ?? [];
  // The saved mic stays in the list even while the PC is off.
  const options = saved && !names.includes(saved) ? [saved, ...names] : names;

  async function pick(value: string) {
    const result = await saveListening({
      mic: value === WINDOWS_DEFAULT ? "" : value,
    });
    if (typeof result === "string") {
      setError(result);
      return;
    }
    setError(null);
    queryClient.setQueryData(END_PAUSE_KEY, result);
  }

  return (
    <div>
      <label htmlFor={micId} className={LABEL_CLASS}>
        PC mic for &quot;Hey Venus&quot;
      </label>
      <Select value={saved || WINDOWS_DEFAULT} onValueChange={pick}>
        <SelectTrigger id={micId} className={SELECT_TRIGGER_CLASS}>
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={WINDOWS_DEFAULT}>Windows default</SelectItem>
          {options.map((name) => (
            <SelectItem key={name} value={name}>
              {name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {mics.isSuccess && names.length === 0 && (
        <p className="mt-1 text-sm text-muted-foreground">
          Start Venus on your PC to see its mics.
        </p>
      )}
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
