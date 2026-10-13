"use client";

import { CalendarClock, Info, Megaphone, Reply, Sparkles, X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type OverviewItem = { uid: string; sender: string; subject: string; unread: boolean; note: string };
export type Overview = { groups: { kind: "reply" | "deadline" | "update" | "promo"; items: OverviewItem[] }[]; summary?: string };

const KINDS = {
  reply: { title: "Needs a reply", icon: Reply, accent: "text-primary" },
  deadline: { title: "Deadlines", icon: CalendarClock, accent: "text-amber-600 dark:text-amber-400" },
  update: { title: "Updates", icon: Info, accent: "text-sky-600 dark:text-sky-400" },
  promo: { title: "Promotions", icon: Megaphone, accent: "text-muted-foreground" },
};

// Luna's inbox overview as groups; each line opens that email.
export default function InboxOverview({ overview, onOpen, onClose }: { overview: Overview; onOpen: (uid: string) => void; onClose: () => void }) {
  const empty = overview.groups.length === 0 && !overview.summary;
  return (
    <section aria-label="Inbox overview" className="rounded-xl border border-border bg-card p-3">
      <div className="mb-2 flex items-center gap-2">
        <Sparkles className="size-4 text-primary" aria-hidden="true" />
        <h2 className="text-sm font-semibold">Overview</h2>
        <Button variant="ghost" size="icon-sm" className="ml-auto" aria-label="Close overview" onClick={onClose}>
          <X />
        </Button>
      </div>
      {empty && <p className="px-1 text-sm text-muted-foreground">Nothing in your inbox.</p>}
      {overview.summary && <p className="whitespace-pre-wrap px-1 text-sm leading-relaxed">{overview.summary}</p>}
      {overview.groups.length > 0 && (
        <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
          {overview.groups.map((group) => {
            const kind = KINDS[group.kind];
            const Icon = kind.icon;
            return (
              <div key={group.kind} className="rounded-lg border border-border bg-background/60 p-2">
                <p className={cn("mb-1 flex items-center gap-1.5 px-1 text-xs font-semibold", kind.accent)}>
                  <Icon className="size-3.5" aria-hidden="true" />
                  {kind.title}
                  <span className="ml-auto font-normal text-muted-foreground">{group.items.length}</span>
                </p>
                <ul>
                  {group.items.map((item) => (
                    <li key={item.uid}>
                      <button
                        type="button"
                        onClick={() => onOpen(item.uid)}
                        className="w-full rounded-md px-1.5 py-1.5 text-left hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
                      >
                        <span className={cn("block truncate text-sm", item.unread && "font-semibold")}>{item.subject}</span>
                        <span className="block truncate text-xs text-muted-foreground">
                          {item.sender}
                          {item.note && ` · ${item.note}`}
                        </span>
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}
