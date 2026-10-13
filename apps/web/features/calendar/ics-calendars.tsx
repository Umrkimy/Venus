"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarDays, Link2, Trash2 } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import { getJson } from "@/lib/get-json";

type IcsCalendar = { id: string; name: string; kind: "link" | "file" };

// A whole semester's timetable is well under this; Venus refuses bigger.
const MAX_BYTES = 2_000_000;

function message(data: { detail?: unknown }, fallback: string) {
  const first = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : fallback;
}

// Settings, Calendar: timetables and other calendars from an .ics link or file.
export default function IcsCalendars() {
  const fileInput = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const calendars = useQuery({
    queryKey: ["ics-calendars"],
    queryFn: () => getJson<IcsCalendar[]>("/api/calendar/ics"),
  });

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setNotice(null);
    if (file && file.size > MAX_BYTES) {
      setError("That file is too big (over 2 MB).");
      return;
    }
    setBusy(true);
    try {
      const body = file ? { name: name.trim(), content: await file.text() } : { name: name.trim(), url: url.trim() };
      const response = await fetch("/api/calendar/ics", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        setError(message(data, "Couldn't add that calendar."));
        return;
      }
      setName("");
      setUrl("");
      setFile(null);
      if (fileInput.current) fileInput.current.value = "";
      const count = data.events_next_4_weeks as number;
      setNotice(
        `Added ${data.name}: ${count} ${count === 1 ? "event" : "events"} in the next 4 weeks. Try "what's on tomorrow?"`,
      );
      await calendars.refetch();
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  async function remove(calendar: IcsCalendar) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const response = await fetch(`/api/calendar/ics/${calendar.id}`, { method: "DELETE" });
      if (!response.ok) setError(`Couldn't remove ${calendar.name}.`);
      await calendars.refetch();
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>

      {calendars.isSuccess && calendars.data.length > 0 && (
        <ul className="mb-4 space-y-2">
          {calendars.data.map((calendar) => {
            const Icon = calendar.kind === "link" ? Link2 : CalendarDays;
            return (
              <li
                key={calendar.id}
                className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 hover:border-foreground/30 hover:bg-muted/60"
              >
                <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{calendar.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {calendar.kind === "link" ? "Link, updates itself" : "File, upload again when it changes"}
                  </p>
                </div>
                <Button
                  type="button"
                  variant="ghost"
                  size="icon-sm"
                  disabled={busy}
                  onClick={() => remove(calendar)}
                  aria-label={`Remove ${calendar.name}`}
                >
                  <Trash2 />
                </Button>
              </li>
            );
          })}
        </ul>
      )}
      {calendars.isError && (
        <p role="alert" className="mt-4 text-sm text-destructive">
          Can&apos;t load your calendars.
        </p>
      )}

      <form onSubmit={add} className="space-y-4">
        <label className={LABEL_CLASS}>
          Name
          <Input
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Uni timetable"
            maxLength={40}
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <label className={LABEL_CLASS}>
          Link
          <Input
            value={url}
            onChange={(event) => {
              setUrl(event.target.value);
              if (event.target.value) setFile(null);
            }}
            placeholder="https://... or webcal://..."
            disabled={file !== null}
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <div>
          <p className={LABEL_CLASS}>Or a file</p>
          <input
            ref={fileInput}
            type="file"
            accept=".ics,text/calendar"
            aria-label="Calendar file (.ics)"
            disabled={url.trim() !== ""}
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm text-muted-foreground file:mr-3 file:rounded-md file:border file:border-border file:bg-transparent file:px-3 file:py-1.5 file:text-sm file:text-foreground hover:file:bg-muted"
          />
        </div>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy || !name.trim() || (!url.trim() && !file)}>
            Add calendar
          </Button>
          <p aria-live="polite" className="text-sm">
            {error && <span className="text-destructive">{error}</span>}
            {notice && <span className="text-muted-foreground">{notice}</span>}
          </p>
        </div>
      </form>
    </div>
  );
}
