"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FIELD_HOVER, LABEL_CLASS, SELECT_TRIGGER_CLASS } from "@/features/settings/field-styles";

export type CalendarEvent = {
  id: string;
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  source: string;
  location: string;
  notes: string;
  editable: boolean;
};

export type EventDraft = {
  title: string;
  start: string;
  end: string;
  all_day: boolean;
  location: string;
  notes: string;
  calendar?: string;
};

export type DialogState =
  | { mode: "new"; start: Date; end: Date; allDay: boolean }
  | { mode: "edit"; event: CalendarEvent };

const pad = (n: number) => String(n).padStart(2, "0");
// <input type="datetime-local"> and type="date" speak local time without a zone.
const localDate = (d: Date) => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
const localDateTime = (d: Date) => `${localDate(d)}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
const DAY = 24 * 60 * 60 * 1000;

function dayAt(value: string) {
  // "2026-10-20" as midnight UTC: how Venus stores all-day events.
  return new Date(`${value}T00:00:00Z`);
}

type Props = {
  state: DialogState | null;
  calendars: { id: string; label: string }[];
  busy: boolean;
  error: string | null;
  onClose: () => void;
  onSave: (draft: EventDraft) => void;
  onDelete: (event: CalendarEvent) => void;
};

// Add, change or delete one event; timetable (.ics) events are shown read-only.
export default function EventDialog({ state, calendars, busy, error, onClose, onSave, onDelete }: Props) {
  return (
    <Dialog open={state !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        {state && (
          <EventForm
            key={state.mode === "edit" ? state.event.id : `${state.start.getTime()}`}
            state={state}
            calendars={calendars}
            busy={busy}
            error={error}
            onClose={onClose}
            onSave={onSave}
            onDelete={onDelete}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function EventForm({ state, calendars, busy, error, onClose, onSave, onDelete }: Props & { state: DialogState }) {
  const event = state.mode === "edit" ? state.event : null;
  const readOnly = event !== null && !event.editable;
  const startAt = event ? new Date(event.start) : (state as { start: Date }).start;
  const endAt = event ? new Date(event.end) : (state as { end: Date }).end;
  const initialAllDay = event ? event.all_day : (state as { allDay: boolean }).allDay;

  const [title, setTitle] = useState(event?.title ?? "");
  const [allDay, setAllDay] = useState(initialAllDay);
  // All-day: the dates as shown; the end date is the last day, inclusive. Saved
  // all-day events are UTC days; a new selection from the grid is in local time.
  const lastDay = new Date(endAt.getTime() - (initialAllDay ? DAY : 0));
  const savedAllDay = event !== null && initialAllDay;
  const [startDay, setStartDay] = useState(savedAllDay ? startAt.toISOString().slice(0, 10) : localDate(startAt));
  const [endDay, setEndDay] = useState(savedAllDay ? lastDay.toISOString().slice(0, 10) : localDate(lastDay));
  const [start, setStart] = useState(localDateTime(startAt));
  const [end, setEnd] = useState(localDateTime(endAt));
  const [location, setLocation] = useState(event?.location ?? "");
  const [notes, setNotes] = useState(event?.notes ?? "");
  const [calendar, setCalendar] = useState("venus");

  function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const times = allDay
      ? { start: dayAt(startDay).toISOString(), end: new Date(dayAt(endDay).getTime() + DAY).toISOString() }
      : { start: new Date(start).toISOString(), end: new Date(end).toISOString() };
    onSave({
      title: title.trim(),
      ...times,
      all_day: allDay,
      location: location.trim(),
      notes,
      ...(event ? {} : { calendar }),
    });
  }

  if (readOnly) {
    return (
      <>
        <DialogHeader>
          <DialogTitle>{event.title}</DialogTitle>
          <DialogDescription>From {event.source}. Change it there; Venus only reads it.</DialogDescription>
        </DialogHeader>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="text-muted-foreground">When</dt>
            <dd>{describe(event)}</dd>
          </div>
          {event.location && (
            <div>
              <dt className="text-muted-foreground">Where</dt>
              <dd>{event.location}</dd>
            </div>
          )}
          {event.notes && (
            <div>
              <dt className="text-muted-foreground">Notes</dt>
              <dd className="whitespace-pre-wrap">{event.notes}</dd>
            </div>
          )}
        </dl>
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onClose}>
            Close
          </Button>
        </DialogFooter>
      </>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <DialogHeader>
        <DialogTitle>{event ? "Edit event" : "New event"}</DialogTitle>
        {event && <DialogDescription>On your {event.source} calendar.</DialogDescription>}
      </DialogHeader>
      <label className={LABEL_CLASS}>
        Title
        <Input
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          maxLength={200}
          placeholder="Gym"
          autoComplete="off"
          autoFocus
          className={FIELD_HOVER}
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input
          type="checkbox"
          className="size-4 accent-primary"
          checked={allDay}
          onChange={(e) => setAllDay(e.target.checked)}
        />
        All day
      </label>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={LABEL_CLASS}>
          Starts
          {allDay ? (
            <Input type="date" value={startDay} onChange={(e) => setStartDay(e.target.value)} className={FIELD_HOVER} />
          ) : (
            <Input type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} className={FIELD_HOVER} />
          )}
        </label>
        <label className={LABEL_CLASS}>
          Ends
          {allDay ? (
            <Input type="date" value={endDay} onChange={(e) => setEndDay(e.target.value)} className={FIELD_HOVER} />
          ) : (
            <Input type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} className={FIELD_HOVER} />
          )}
        </label>
      </div>
      <label className={LABEL_CLASS}>
        Where
        <Input
          value={location}
          onChange={(e) => setLocation(e.target.value)}
          maxLength={200}
          placeholder="Optional"
          autoComplete="off"
          className={FIELD_HOVER}
        />
      </label>
      <label className={LABEL_CLASS}>
        Notes
        <Textarea value={notes} onChange={(e) => setNotes(e.target.value)} maxLength={5000} rows={3} className="mt-1.5" />
      </label>
      {!event && calendars.length > 1 && (
        <div>
          <label htmlFor="event-calendar" className={LABEL_CLASS}>
            Calendar
          </label>
          <Select value={calendar} onValueChange={setCalendar}>
            <SelectTrigger id="event-calendar" className={SELECT_TRIGGER_CLASS}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {calendars.map((option) => (
                <SelectItem key={option.id} value={option.id}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <DialogFooter className="gap-2 sm:justify-between">
        {event ? (
          <Button type="button" variant="ghost" className="text-destructive" disabled={busy} onClick={() => onDelete(event)}>
            Delete
          </Button>
        ) : (
          <span />
        )}
        <div className="flex gap-2">
          <Button type="button" variant="outline" onClick={() => onClose()} disabled={busy}>
            Cancel
          </Button>
          <Button type="submit" disabled={busy || !title.trim()}>
            {busy ? "Saving..." : "Save"}
          </Button>
        </div>
      </DialogFooter>
    </form>
  );
}

function describe(event: CalendarEvent) {
  const start = new Date(event.start);
  const end = new Date(event.end);
  if (event.all_day) {
    const last = new Date(end.getTime() - DAY);
    const day = (d: Date) => d.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short", timeZone: "UTC" });
    return last.getTime() > start.getTime() ? `${day(start)} to ${day(last)}` : `${day(start)}, all day`;
  }
  const when = start.toLocaleString(undefined, { weekday: "short", day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
  return `${when} to ${end.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}
