"use client";

import { useQueries, useQuery } from "@tanstack/react-query";
import { CalendarDays, ChevronDown, Mail } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import type { CalendarEvent } from "@/features/calendar/event-dialog";
import ReconnectButton, { SignInNotice, isSignInProvider, type SignInProvider } from "@/features/calendar/reconnect-button";
import { useEmailAccounts } from "@/features/email/email-accounts";
import { inboxQuery } from "@/features/email/mail-api";
import { getJson } from "@/lib/get-json";
import { cn } from "@/lib/utils";

const SHOWN = 4;

function localDay(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
}

// All-day events are whole dates (end is the day after); timed ones overlap today.
function todaysEvents(events: CalendarEvent[], now: Date) {
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

function time(event: CalendarEvent) {
  return event.all_day
    ? "All day"
    : new Date(event.start).toLocaleTimeString(undefined, {
        hour: "numeric",
        minute: "2-digit",
      });
}

// Home, before the first message: today's events and new mail. No AI, nothing sent anywhere.
export default function TodayCard() {
  const now = new Date();
  // Phones: one line until tapped, so Venus stays in view.
  const [open, setOpen] = useState(false);
  const week = useQuery({
    queryKey: ["calendar-week"],
    queryFn: () =>
      getJson<{ events: CalendarEvent[]; errors: string[]; signed_out?: SignInProvider[] }>(
        "/api/calendar/events",
      ),
    staleTime: 5 * 60_000,
  });
  const accounts = useEmailAccounts();
  const inboxes = useQueries({
    queries: (accounts.data ?? []).map((account) => ({
      ...inboxQuery(account.id),
      staleTime: 5 * 60_000,
    })),
  });

  const events = todaysEvents(week.data?.events ?? [], now);
  const hasMail = (accounts.data?.length ?? 0) > 0;
  const calendarSignedOut = week.data?.signed_out ?? [];
  if (!hasMail && events.length === 0 && calendarSignedOut.length === 0) return null;

  const fresh = inboxes.reduce(
    (sum, inbox) =>
      sum +
      (inbox.data?.filter((item) => item.unread && item.category === "primary")
        .length ?? 0),
    0,
  );
  const failed = inboxes.filter((inbox) => inbox.isError).length;
  // Signed out by Google or Microsoft: one button each, right here.
  const signedOut = new Set<SignInProvider>(calendarSignedOut);
  inboxes.forEach((inbox, index) => {
    const kind = accounts.data?.[index]?.kind;
    if (inbox.isError && isSignInProvider(kind) && /signed Venus out/.test(inbox.error.message)) signedOut.add(kind);
  });
  const loading = inboxes.some((inbox) => inbox.isPending);

  return (
    <section
      aria-label="Today"
      className="rounded-xl border border-border bg-background/70 p-3 text-sm shadow-sm backdrop-blur-md"
    >
      <button
        type="button"
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        className="flex w-full cursor-pointer items-center gap-2 text-left sm:pointer-events-none"
      >
        <span className="text-xs font-medium tracking-wide text-muted-foreground uppercase">
          {now.toLocaleDateString(undefined, {
            weekday: "long",
            day: "numeric",
            month: "short",
          })}
        </span>
        {!open && (
          <span className="text-xs sm:hidden">
            {events.length} {events.length === 1 ? "event" : "events"}
            {hasMail && !loading && `, ${fresh} new mail`}
          </span>
        )}
        <ChevronDown
          className={cn("ml-auto size-3.5 sm:hidden", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      <div className={cn(!open && "hidden sm:block")}>
        <ul className="mt-2 space-y-1">
          {events.length === 0 && (
            <li className="text-muted-foreground">Nothing on today.</li>
          )}
          {events.slice(0, SHOWN).map((event) => (
            <li
              key={event.id}
              className={cn(
                "flex gap-2",
                !event.all_day &&
                  new Date(event.end) < now &&
                  "text-muted-foreground line-through",
              )}
            >
              <CalendarDays
                className="mt-0.5 size-3.5 shrink-0 text-primary"
                aria-hidden="true"
              />
              <span className="w-16 shrink-0 whitespace-nowrap tabular-nums">
                {time(event)}
              </span>
              <span className="min-w-0 truncate">{event.title}</span>
            </li>
          ))}
          {events.length > SHOWN && (
            <li>
              <Link
                href="/calendar"
                className="text-xs text-primary hover:underline"
              >
                {events.length - SHOWN} more today
              </Link>
            </li>
          )}
        </ul>
        {hasMail && (
          <Link
            href="/email"
            className="mt-2 flex items-center gap-2 rounded-md hover:text-primary"
          >
            <Mail
              className="size-3.5 shrink-0 text-primary"
              aria-hidden="true"
            />
            {loading ? (
              <span className="text-muted-foreground">Checking mail...</span>
            ) : (
              <span>
                {fresh === 0 ? "No new mail" : `${fresh} new in Primary`}
                {failed > 0 && (
                  <span className="text-muted-foreground">
                    {" "}
                    ({failed === 1 ? "one mailbox" : `${failed} mailboxes`}{" "}
                    didn&apos;t answer)
                  </span>
                )}
              </span>
            )}
          </Link>
        )}
      </div>
      {signedOut.size > 0 && (
        <div className="mt-2 space-y-1.5 border-t border-border pt-2">
          <p className="text-xs text-muted-foreground">Signed out, so some events or mail are missing.</p>
          <div className="flex flex-wrap gap-1.5">
            {[...signedOut].map((provider) => (
              <ReconnectButton key={provider} provider={provider} back="home" size="xs" />
            ))}
          </div>
        </div>
      )}
      <div className="mt-2 empty:hidden">
        <SignInNotice />
      </div>
    </section>
  );
}
