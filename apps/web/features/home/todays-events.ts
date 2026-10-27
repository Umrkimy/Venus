import type { CalendarEvent } from "@/features/calendar/event-dialog";

function localDay(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

// All-day events are whole dates (end is the day after); timed ones overlap today.
export function todaysEvents(events: CalendarEvent[], now: Date) {
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const end = new Date(
    start.getFullYear(),
    start.getMonth(),
    start.getDate() + 1,
  );
  const today = localDay(now);
  return events.filter((event) =>
    event.all_day
      ? event.start.slice(0, 10) <= today && today < event.end.slice(0, 10)
      : new Date(event.start) < end && new Date(event.end) > start,
  );
}
