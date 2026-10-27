import { describe, expect, it } from "vitest";

import type { CalendarEvent } from "@/features/calendar/event-dialog";

import { todaysEvents } from "./todays-events";

function event(title: string, start: string, end: string, all_day = false): CalendarEvent {
  return { id: title, title, start, end, all_day, source: "Venus", location: "", notes: "", editable: true };
}

// Local time, so the test means the same in any time zone.
const NOW = new Date(2026, 9, 28, 9, 30);
const at = (day: number, hour: number) => new Date(2026, 9, day, hour).toISOString();

describe("todaysEvents", () => {
  it("keeps timed events that overlap today", () => {
    const events = [
      event("Lecture", at(28, 10), at(28, 12)),
      event("Late night", at(27, 23), at(28, 1)),
      event("Yesterday", at(27, 10), at(27, 11)),
      event("Tomorrow", at(29, 10), at(29, 11)),
    ];
    expect(todaysEvents(events, NOW).map((each) => each.title)).toEqual(["Lecture", "Late night"]);
  });

  it("treats all-day events as whole dates, end day not included", () => {
    const events = [
      event("Holiday", "2026-10-28", "2026-10-29", true),
      event("Trip", "2026-10-26", "2026-10-30", true),
      event("Ended", "2026-10-27", "2026-10-28", true),
    ];
    expect(todaysEvents(events, NOW).map((each) => each.title)).toEqual(["Holiday", "Trip"]);
  });
});
