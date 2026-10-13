"use client";

import type { DatesSetArg, EventClickArg, EventDropArg, EventInput } from "@fullcalendar/core";
import dayGridPlugin from "@fullcalendar/daygrid";
import interactionPlugin, { type EventResizeDoneArg } from "@fullcalendar/interaction";
import listPlugin from "@fullcalendar/list";
import FullCalendar from "@fullcalendar/react";
import timeGridPlugin from "@fullcalendar/timegrid";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import EventDialog, { type CalendarEvent, type DialogState, type EventDraft } from "@/features/calendar/event-dialog";
import { getJson } from "@/lib/get-json";

type EventsResponse = { events: CalendarEvent[]; errors: string[] };
type Range = { start: string; end: string };

// One colour per kind of calendar; .ics timetables share one.
const SOURCE_CLASS: Record<string, string> = {
  Venus: "venus-event-venus",
  Google: "venus-event-google",
  Outlook: "venus-event-outlook",
};

function message(data: { detail?: unknown }, fallback: string) {
  const first = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : fallback;
}

function toInput(event: CalendarEvent): EventInput {
  return {
    id: event.id,
    title: event.title,
    // All-day events are whole UTC days; plain dates keep them on the right day everywhere.
    start: event.all_day ? event.start.slice(0, 10) : event.start,
    end: event.all_day ? event.end.slice(0, 10) : event.end,
    allDay: event.all_day,
    editable: event.editable,
    classNames: [SOURCE_CLASS[event.source] ?? "venus-event-ics"],
    extendedProps: { event },
  };
}

function utcDay(date: Date) {
  // FullCalendar gives all-day dates as local midnight; Venus stores that day at UTC midnight.
  return new Date(Date.UTC(date.getFullYear(), date.getMonth(), date.getDate())).toISOString();
}

// The Calendar page: every calendar in one view; add, move and change events.
export default function CalendarPage() {
  const queryClient = useQueryClient();
  const [range, setRange] = useState<Range | null>(null);
  const [dialog, setDialog] = useState<DialogState | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const events = useQuery({
    queryKey: ["calendar-events", range],
    queryFn: () =>
      getJson<EventsResponse>(
        `/api/calendar/events?start=${encodeURIComponent(range!.start)}&end=${encodeURIComponent(range!.end)}`,
      ),
    enabled: range !== null,
    placeholderData: (previous) => previous,
  });
  const calendars = useQuery({
    queryKey: ["calendar-writable"],
    queryFn: () => getJson<{ id: string; label: string }[]>("/api/calendar/writable"),
  });

  async function send(path: string, method: string, body?: unknown) {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = response.status === 204 ? {} : await response.json();
    if (!response.ok) throw new Error(message(data, "Couldn't save that."));
    return data;
  }

  async function refresh() {
    await queryClient.invalidateQueries({ queryKey: ["calendar-events"] });
  }

  async function save(draft: EventDraft) {
    if (!dialog) return;
    setBusy(true);
    setError(null);
    try {
      if (dialog.mode === "edit") {
        await send(`/api/calendar/events/${encodeURIComponent(dialog.event.id)}`, "PATCH", draft);
      } else {
        await send("/api/calendar/events", "POST", draft);
      }
      setDialog(null);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Couldn't save that.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(event: CalendarEvent) {
    setBusy(true);
    setError(null);
    try {
      await send(`/api/calendar/events/${encodeURIComponent(event.id)}`, "DELETE");
      setDialog(null);
      await refresh();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Couldn't delete that.");
    } finally {
      setBusy(false);
    }
  }

  // Dragging an event to another time, or stretching it.
  async function moved(info: EventDropArg | EventResizeDoneArg) {
    const event = info.event.extendedProps.event as CalendarEvent;
    const start = info.event.start!;
    const end = info.event.end ?? new Date(start.getTime() + (info.event.allDay ? 86_400_000 : 3_600_000));
    setNotice(null);
    try {
      await send(`/api/calendar/events/${encodeURIComponent(event.id)}`, "PATCH", {
        title: event.title,
        start: info.event.allDay ? utcDay(start) : start.toISOString(),
        end: info.event.allDay ? utcDay(end) : end.toISOString(),
        all_day: info.event.allDay,
        location: event.location,
        notes: event.notes,
      });
      await refresh();
    } catch (exc) {
      info.revert();
      setNotice(exc instanceof Error ? exc.message : "Couldn't move that event.");
    }
  }

  function open(state: DialogState) {
    setError(null);
    setDialog(state);
  }

  const problems = [...(events.data?.errors ?? []), ...(notice ? [notice] : [])];

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-4 pb-4">
      <div className="flex flex-wrap items-center gap-3">
        <h1 className="text-lg font-semibold tracking-tight">Calendar</h1>
        <p className="hidden text-sm text-muted-foreground sm:block">
          Click a day or drag over times to add. Timetables (.ics) are read-only.
        </p>
        <div className="ml-auto flex items-center gap-2">
          <Button variant="ghost" size="sm" asChild>
            <Link href="/settings/calendar">Connect calendars</Link>
          </Button>
          <Button
            size="sm"
            onClick={() => {
              const start = new Date();
              start.setMinutes(0, 0, 0);
              start.setHours(start.getHours() + 1);
              open({ mode: "new", start, end: new Date(start.getTime() + 3_600_000), allDay: false });
            }}
          >
            <Plus />
            New event
          </Button>
        </div>
      </div>
      {problems.length > 0 && (
        <p role="alert" className="text-sm text-destructive">
          {problems.join(" · ")}
        </p>
      )}
      {events.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load your calendar.
        </p>
      )}
      <div className="venus-calendar min-h-0 flex-1 overflow-auto rounded-xl border border-border bg-card p-2 sm:p-3">
        <FullCalendar
          plugins={[dayGridPlugin, timeGridPlugin, listPlugin, interactionPlugin]}
          initialView="dayGridMonth"
          headerToolbar={{
            left: "prev,next today",
            center: "title",
            right: "dayGridMonth,timeGridWeek,timeGridDay,listWeek",
          }}
          buttonText={{ today: "Today", month: "Month", week: "Week", day: "Day", list: "List" }}
          height="100%"
          nowIndicator
          selectable
          selectMirror
          dayMaxEvents
          eventTimeFormat={{ hour: "numeric", minute: "2-digit", meridiem: "short" }}
          events={(events.data?.events ?? []).map(toInput)}
          datesSet={(info: DatesSetArg) =>
            setRange((old) =>
              old && old.start === info.startStr && old.end === info.endStr
                ? old
                : { start: info.start.toISOString(), end: info.end.toISOString() },
            )
          }
          select={(info) => {
            info.view.calendar.unselect();
            // A single click picks one half-hour slot; an hour is a better start.
            const short = !info.allDay && info.end.getTime() - info.start.getTime() <= 30 * 60_000;
            const end = short ? new Date(info.start.getTime() + 3_600_000) : info.end;
            open({ mode: "new", start: info.start, end, allDay: info.allDay });
          }}
          eventClick={(info: EventClickArg) => open({ mode: "edit", event: info.event.extendedProps.event as CalendarEvent })}
          eventDrop={moved}
          eventResize={moved}
        />
      </div>
      <EventDialog
        state={dialog}
        calendars={calendars.data ?? [{ id: "venus", label: "Venus" }]}
        busy={busy}
        error={error}
        onClose={() => setDialog(null)}
        onSave={save}
        onDelete={remove}
      />
    </div>
  );
}
