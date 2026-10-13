"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Inbox, Paperclip, PenLine, RefreshCw, Reply, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Textarea } from "@/components/ui/textarea";
import Composer, { type Draft } from "@/features/email/composer";
import { useEmailAccounts } from "@/features/email/email-accounts";
import InboxOverview, { type Overview } from "@/features/email/inbox-overview";
import MailBody from "@/features/email/mail-body";
import TonePicker, { SenderAvatar, type Tone } from "@/features/email/tone-picker";
import { cn } from "@/lib/utils";

type Summary = { uid: string; sender: string; sender_address: string; subject: string; date: string | null; unread: boolean };
type Message = Summary & { to: string[]; cc: string[]; body: string; html: string; attachments: string[] };

export function errorText(data: { detail?: unknown }, fallback: string) {
  const first = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : fallback;
}

async function load<T>(path: string): Promise<T> {
  const response = await fetch(path);
  const data = await response.json();
  if (!response.ok) throw new Error(errorText(data, "Couldn't load that."));
  return data as T;
}

function when(date: string | null) {
  if (!date) return "";
  const moment = new Date(date);
  const today = new Date();
  return moment.toDateString() === today.toDateString()
    ? moment.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
    : moment.toLocaleDateString(undefined, { day: "numeric", month: "short" });
}

// The Email page: inbox on the left, the open message and Luna's help on the right.
export default function EmailPage() {
  const queryClient = useQueryClient();
  const accounts = useEmailAccounts();
  const [chosen, setChosen] = useState<string | null>(null);
  const accountId = chosen ?? accounts.data?.[0]?.id ?? null;
  const account = accounts.data?.find((item) => item.id === accountId);
  const [open, setOpen] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [overview, setOverview] = useState<Overview | null>(null);
  const [summary, setSummary] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [tone, setTone] = useState<Tone>("professional");
  const [wish, setWish] = useState("");

  const inbox = useQuery({
    queryKey: ["email-inbox", accountId],
    queryFn: () => load<Summary[]>(`/api/email/accounts/${accountId}/messages`),
    enabled: accountId !== null,
    retry: false,
  });
  const message = useQuery({
    queryKey: ["email-message", accountId, open],
    queryFn: () => load<Message>(`/api/email/accounts/${accountId}/messages/${open}`),
    enabled: accountId !== null && open !== null,
    retry: false,
  });

  // Opening marks it read on the server: refresh the list once it has.
  const openedUid = message.data?.uid;
  useEffect(() => {
    if (openedUid) queryClient.invalidateQueries({ queryKey: ["email-inbox", accountId] });
  }, [openedUid, accountId, queryClient]);

  async function post<T>(path: string, body?: unknown): Promise<T> {
    const response = await fetch(path, {
      method: "POST",
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await response.json();
    if (!response.ok) throw new Error(errorText(data, "That didn't work."));
    return data as T;
  }

  async function run(what: string, job: () => Promise<void>) {
    setBusy(what);
    setError(null);
    try {
      await job();
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "That didn't work.");
    } finally {
      setBusy(null);
    }
  }

  function choose(uid: string) {
    // Opening marks it read on the server; show that in the list at once.
    queryClient.setQueryData<Summary[]>(["email-inbox", accountId], (items) =>
      items?.map((item) => (item.uid === uid ? { ...item, unread: false } : item)),
    );
    setOpen(uid);
    setSummary(null);
    setDraft(null);
    setWish("");
    setError(null);
    setNotice(null);
  }

  function compose(next: Draft) {
    setError(null);
    setNotice(null);
    setDraft(next);
  }

  if (accounts.isSuccess && accounts.data.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-4 px-4 text-center">
        <span className="flex size-14 items-center justify-center rounded-2xl bg-primary/10 text-primary">
          <Inbox className="size-7" aria-hidden="true" />
        </span>
        <div>
          <h1 className="text-lg font-semibold">Your inbox lives here</h1>
          <p className="mt-1 max-w-md text-sm text-muted-foreground">
            Add a mailbox and Venus can show your mail, sum it up, and write replies for you to check and send.
          </p>
        </div>
        <Button asChild>
          <Link href="/settings/email">Add an email account</Link>
        </Button>
      </div>
    );
  }

  const reader = open !== null;
  const unread = inbox.data?.filter((item) => item.unread).length ?? 0;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-4 pb-4">
      <header className="flex flex-wrap items-center gap-2">
        <div className="mr-auto flex min-w-0 items-center gap-2">
          <h1 className="text-lg font-semibold tracking-tight">Inbox</h1>
          {unread > 0 && (
            <span className="rounded-full bg-primary/15 px-2 py-0.5 text-xs font-medium text-primary">{unread} unread</span>
          )}
          {accounts.data && accounts.data.length > 1 ? (
            <Select
              value={accountId ?? undefined}
              onValueChange={(value) => {
                setChosen(value);
                setOpen(null);
                setOverview(null);
                setDraft(null);
              }}
            >
              <SelectTrigger className="h-8 w-56" aria-label="Mailbox">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {accounts.data.map((item) => (
                  <SelectItem key={item.id} value={item.id}>
                    {item.address}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          ) : (
            <span className="truncate text-sm text-muted-foreground">{account?.address}</span>
          )}
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={busy !== null || accountId === null}
          onClick={() =>
            run("overview", async () => {
              setOverview(await post<Overview>(`/api/email/accounts/${accountId}/summary`));
            })
          }
        >
          <Sparkles className="text-primary" />
          {busy === "overview" ? "Reading..." : "Sum up inbox"}
        </Button>
        <Button variant="ghost" size="icon-sm" aria-label="Refresh" onClick={() => inbox.refetch()} disabled={inbox.isFetching}>
          <RefreshCw className={cn(inbox.isFetching && "motion-safe:animate-spin")} />
        </Button>
        <Button
          size="sm"
          onClick={() => {
            setOpen(null);
            compose({ to: [], cc: [], subject: "", body: "", reply_to: null });
          }}
        >
          <PenLine />
          Write
        </Button>
      </header>

      {error && (
        <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="rounded-lg border border-border bg-muted/60 px-3 py-2 text-sm">
          {notice}
        </p>
      )}
      {overview && <InboxOverview overview={overview} onOpen={choose} onClose={() => setOverview(null)} />}

      <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[minmax(18rem,24rem)_1fr]">
        <section
          aria-label="Messages"
          className={cn("min-h-0 overflow-auto rounded-xl border border-border bg-card p-1.5", (reader || draft) && "hidden md:block")}
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
            <p role="alert" className="p-3 text-sm text-destructive">
              {inbox.error.message}
            </p>
          )}
          {inbox.data?.length === 0 && <p className="p-3 text-sm text-muted-foreground">Your inbox is empty.</p>}
          <ul className="space-y-0.5">
            {inbox.data?.map((item) => {
              const active = open === item.uid;
              return (
                <li key={item.uid}>
                  <button
                    type="button"
                    onClick={() => choose(item.uid)}
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

        <section aria-label="Message" className={cn("min-h-0 overflow-auto", !reader && !draft && "hidden md:block")}>
          {draft ? (
            <Composer
              // A new draft (from Luna or another message) starts a fresh form.
              key={`${draft.reply_to}:${draft.subject}:${draft.body.length}`}
              accountId={accountId!}
              draft={draft}
              onClose={() => setDraft(null)}
              onSent={(to) => {
                setDraft(null);
                setNotice(`Sent to ${to.join(", ")}.`);
                inbox.refetch();
              }}
            />
          ) : reader ? (
            <article className="rounded-xl border border-border bg-card">
              <div className="space-y-4 p-4 sm:p-5">
                <Button variant="ghost" size="sm" className="-ml-2 md:hidden" onClick={() => setOpen(null)}>
                  <ArrowLeft />
                  Inbox
                </Button>
                {message.isPending && (
                  <div className="space-y-3" role="status">
                    <span className="sr-only">Opening</span>
                    <div className="h-6 w-2/3 rounded bg-foreground/10 motion-safe:animate-pulse" />
                    <div className="h-4 w-1/2 rounded bg-foreground/10 motion-safe:animate-pulse" />
                    <div className="h-32 rounded bg-foreground/10 motion-safe:animate-pulse" />
                  </div>
                )}
                {message.isError && (
                  <p role="alert" className="text-sm text-destructive">
                    {message.error.message}
                  </p>
                )}
                {message.data && (
                  <>
                    <h2 className="text-xl font-semibold leading-snug tracking-tight">{message.data.subject}</h2>
                    <div className="flex items-center gap-3">
                      <SenderAvatar name={message.data.sender || message.data.sender_address} className="size-10" />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">{message.data.sender}</p>
                        <p className="truncate text-xs text-muted-foreground">{message.data.sender_address}</p>
                      </div>
                      {message.data.date && (
                        <time className="shrink-0 text-xs text-muted-foreground" dateTime={message.data.date}>
                          {new Date(message.data.date).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" })}
                        </time>
                      )}
                    </div>
                    {message.data.attachments.length > 0 && (
                      <ul className="flex flex-wrap gap-1.5">
                        {message.data.attachments.map((name, index) => (
                          <li key={index} className="flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground">
                            <Paperclip className="size-3" aria-hidden="true" />
                            {name}
                          </li>
                        ))}
                      </ul>
                    )}
                    {summary && (
                      <div className="rounded-lg border border-primary/25 bg-primary/5 p-3 text-sm">
                        <p className="mb-1 flex items-center gap-1.5 text-xs font-medium text-primary">
                          <Sparkles className="size-3.5" aria-hidden="true" /> Luna&apos;s summary
                        </p>
                        <p className="whitespace-pre-wrap leading-relaxed">{summary}</p>
                      </div>
                    )}
                    <MailBody key={message.data.uid} html={message.data.html} text={message.data.body} />
                  </>
                )}
              </div>

              {message.data && (
                <div className="space-y-3 border-t border-border bg-muted/30 p-4 sm:p-5">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="mr-auto flex items-center gap-1.5 text-sm font-semibold">
                      <Sparkles className="size-4 text-primary" aria-hidden="true" />
                      Reply with Luna
                    </p>
                    <TonePicker value={tone} onChange={setTone} />
                  </div>
                  <Textarea
                    value={wish}
                    onChange={(e) => setWish(e.target.value)}
                    maxLength={1000}
                    rows={2}
                    placeholder="What should it say? e.g. yes, I'll submit by Friday (optional)"
                    aria-label="What the reply should say"
                    className="resize-none bg-background"
                  />
                  <div className="flex flex-wrap items-center gap-2">
                    <Button
                      disabled={busy !== null}
                      onClick={() =>
                        run("draft", async () => {
                          compose(await post<Draft>(`/api/email/accounts/${accountId}/messages/${open}/draft`, { tone, wish }));
                        })
                      }
                    >
                      <Reply />
                      {busy === "draft" ? "Writing..." : "Write reply"}
                    </Button>
                    <Button
                      variant="outline"
                      disabled={busy !== null}
                      onClick={() =>
                        run("summary", async () => {
                          const data = await post<{ summary: string }>(`/api/email/accounts/${accountId}/messages/${open}/summary`);
                          setSummary(data.summary);
                        })
                      }
                    >
                      <Sparkles />
                      {busy === "summary" ? "Reading..." : "Sum up"}
                    </Button>
                    <Button
                      variant="ghost"
                      className="ml-auto"
                      onClick={() =>
                        compose({
                          to: [message.data!.sender_address],
                          cc: [],
                          subject: /^re:/i.test(message.data!.subject) ? message.data!.subject : `Re: ${message.data!.subject}`,
                          body: "",
                          reply_to: open,
                        })
                      }
                    >
                      Reply myself
                    </Button>
                  </div>
                </div>
              )}
            </article>
          ) : (
            <div className="hidden h-full flex-col items-center justify-center gap-2 rounded-xl border border-dashed border-border text-center md:flex">
              <Inbox className="size-8 text-muted-foreground/60" aria-hidden="true" />
              <p className="text-sm text-muted-foreground">Pick a message to read it.</p>
            </div>
          )}
        </section>
      </div>
      <p className="text-xs text-muted-foreground">
        Luna&apos;s summaries and replies use your AI model. Nothing is sent without you.
      </p>
    </div>
  );
}
