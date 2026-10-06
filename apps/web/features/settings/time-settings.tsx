"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getJson } from "@/lib/get-json";

import { FIELD_HOVER, LABEL_CLASS } from "./field-styles";

type TimeResponse = { time_zone: string | null; country: string };

// The zone this browser runs in, for example "Asia/Kuala_Lumpur".
function browserTimeZone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone;
}

export default function TimeSettings() {
  const time = useQuery({
    queryKey: ["time"],
    queryFn: () => getJson<TimeResponse>("/api/settings/time"),
  });

  if (time.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading time settings</span>
        <div className="h-8 w-36 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (time.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the time settings.
      </p>
    );
  }

  return <TimeForm initial={time.data} />;
}

function TimeForm({ initial }: { initial: TimeResponse }) {
  // Nothing saved yet: start from this browser's zone, so Save is one click.
  const [timeZone, setTimeZone] = useState(initial.time_zone ?? browserTimeZone());
  const [country, setCountry] = useState(initial.country);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(
    initial.time_zone ? null : "Not saved yet: Luna uses UTC until you save.",
  );
  const [error, setError] = useState<string | null>(null);
  // Every zone name the browser knows, for the suggestions list.
  const [zones] = useState(() => Intl.supportedValuesOf("timeZone"));

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const response = await fetch("/api/settings/time", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ time_zone: timeZone.trim(), country: country.trim() }),
      });
      if (response.status === 422) {
        setError("Unknown time zone. Pick one from the list, like Asia/Kuala_Lumpur.");
        return;
      }
      if (!response.ok) {
        setError("Saving time settings failed.");
        return;
      }
      const saved: TimeResponse = await response.json();
      setMessage(`Saved: ${saved.time_zone}${saved.country ? `, ${saved.country}` : ""}`);
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={LABEL_CLASS}>
          Time zone
          <Input
            type="text"
            list="time-zones"
            value={timeZone}
            onChange={(event) => setTimeZone(event.target.value)}
            maxLength={64}
            autoComplete="off"
            placeholder="Asia/Kuala_Lumpur"
            className={FIELD_HOVER}
          />
          <datalist id="time-zones">
            {zones.map((zone) => (
              <option key={zone} value={zone} />
            ))}
          </datalist>
        </label>
        <label className={LABEL_CLASS}>
          Country
          <Input
            type="text"
            value={country}
            onChange={(event) => setCountry(event.target.value)}
            maxLength={60}
            autoComplete="country-name"
            placeholder="Malaysia"
            className={FIELD_HOVER}
          />
        </label>
      </div>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="outline" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </Button>
        <Button type="button" variant="ghost" onClick={() => setTimeZone(browserTimeZone())}>
          Use this browser&apos;s time zone
        </Button>
      </div>
      {message && (
        <p role="status" className="text-sm text-muted-foreground">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </form>
  );
}
