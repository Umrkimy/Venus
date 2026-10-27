"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import ReconnectButton, { isSignInProvider } from "@/features/calendar/reconnect-button";
import type { EmailAccount } from "@/features/email/email-accounts";
import type { Category, Summary } from "@/features/email/mail-api";
import { SenderAvatar } from "@/features/email/tone-picker";
import { cn } from "@/lib/utils";

const TABS: { id: Category; label: string }[] = [
  { id: "primary", label: "Primary" },
  { id: "newsletters", label: "Newsletters" },
  { id: "promotions", label: "Promotions" },
];

function when(date: string | null) {
  if (!date) return "";
  const moment = new Date(date);
  const today = new Date();
  return moment.toDateString() === today.toDateString()
    ? moment.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : moment.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

type Props = {
  inbox: UseQueryResult<Summary[]>;
  account: EmailAccount | undefined;
  tab: Category;
  onTab: (tab: Category) => void;
  open: string | null;
  onChoose: (uid: string) => void;
  hidden: boolean;
};

// The inbox column: Primary / Newsletters / Promotions tabs over the newest mail.
export default function MessageList({ inbox, account, tab, onTab, open, onChoose, hidden }: Props) {
  const shown = inbox.data?.filter((item) => item.category === tab);
  const unreadIn = (category: Category) =>
    inbox.data?.filter((item) => item.unread && item.category === category).length ?? 0;

  return (
    <section
      aria-label="Messages"
      className={cn("min-h-0 overflow-auto rounded-xl border border-border bg-card p-1.5", hidden && "hidden md:block")}
    >
      {inbox.isPending && (
        <div className="space-y-1.5 p-1" role="status">
          <span className="sr-only">Loading your inbox</span>
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="h-14 rounded-lg bg-foreground/10 motion-safe:animate-pulse" />
          ))}
        </div>
      )}
      {inbox.isError && (
        <div role="alert" className="space-y-2 p-3 text-sm">
          <p className="text-destructive">{inbox.error.message}</p>
          {isSignInProvider(account?.kind) && /signed Venus out|isn't connected/.test(inbox.error.message) ? (
            <ReconnectButton provider={account.kind} back="email" />
          ) : (
            <Button asChild size="sm" variant="outline">
              <Link href={account?.kind === "imap" ? "/settings/email" : "/settings/calendar"}>Fix in settings</Link>
            </Button>
          )}
        </div>
      )}
      {inbox.data && (
        <div role="tablist" aria-label="Kind of mail" className="mb-1.5 flex gap-1 rounded-lg bg-muted p-[3px]">
          {TABS.map((item) => {
            const count = unreadIn(item.id);
            return (
              <button
                key={item.id}
                type="button"
                role="tab"
                aria-selected={tab === item.id}
                onClick={() => onTab(item.id)}
                className={cn(
                  "flex flex-1 cursor-pointer items-center justify-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium transition-colors",
                  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                  tab === item.id ? "bg-background text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground",
                )}
              >
                {item.label}
                {count > 0 && <span className="text-primary">{count}</span>}
              </button>
            );
          })}
        </div>
      )}
      {inbox.data?.length === 0 && <p className="p-3 text-sm text-muted-foreground">Your inbox is empty.</p>}
      {inbox.data && inbox.data.length > 0 && shown?.length === 0 && (
        <p className="p-3 text-sm text-muted-foreground">Nothing here in your newest mail.</p>
      )}
      <ul className="space-y-0.5">
        {shown?.map((item) => {
          const active = open === item.uid;
          return (
            <li key={item.uid}>
              <button
                type="button"
                onClick={() => onChoose(item.uid)}
                aria-current={active ? "true" : undefined}
                className={cn(
                  "group relative flex w-full cursor-pointer items-center gap-3 rounded-lg px-2.5 py-2.5 text-left transition-colors",
                  "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
                  active ? "bg-primary/10" : "hover:bg-muted",
                )}
              >
                {active && <span className="absolute inset-y-2 left-0 w-0.5 rounded-full bg-primary" aria-hidden="true" />}
                <SenderAvatar name={item.sender || item.sender_address} />
                <span className="min-w-0 flex-1">
                  <span className="flex items-baseline gap-2">
                    <span className={cn("min-w-0 flex-1 truncate text-sm", item.unread ? "font-semibold" : "font-medium")}>
                      {item.sender || item.sender_address}
                    </span>
                    <span className={cn("shrink-0 text-xs", item.unread ? "font-medium text-primary" : "text-muted-foreground")}>
                      {when(item.date)}
                    </span>
                  </span>
                  <span className="mt-0.5 flex items-center gap-2">
                    <span className={cn("min-w-0 flex-1 truncate text-sm", item.unread ? "text-foreground" : "text-muted-foreground")}>
                      {item.subject}
                    </span>
                    {item.unread && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                  </span>
                </span>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
