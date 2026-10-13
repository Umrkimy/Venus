"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, Paperclip, PenLine, RefreshCw, Reply, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import Composer, { type Draft, type Tone } from "@/features/email/composer";
import { useEmailAccounts } from "@/features/email/email-accounts";
import { cn } from "@/lib/utils";

type Summary = { uid: string; sender: string; sender_address: string; subject: string; date: string | null; unread: boolean };
type Message = Summary & { to: string[]; cc: string[]; body: string; attachments: string[] };

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
  const accounts = useEmailAccounts();
  const [chosen, setChosen] = useState<string | null>(null);
  const accountId = chosen ?? accounts.data?.[0]?.id ?? null;
  const account = accounts.data?.find((item) => item.id === accountId);
  const [open, setOpen] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [overview, setOverview] = useState<string | null>(null);
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
      <div className="flex flex-1 flex-col items-center justify-center gap-3 px-4 text-center">
        <h1 className="text-lg font-semibold">Email</h1>
        <p className="max-w-md text-sm text-muted-foreground">
          Add a mailbox and Venus can show your inbox, sum it up, and write replies for you to check and send.
        </p>
        <Button asChild>
          <Link href="/settings/email">Add an email account</Link>
        </Button>
      </div>
    );
  }

  const reader = open !== null;

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 px-4 pb-4">
      <div className="flex flex-wrap items-center gap-2">
        <h1 className="text-lg font-semibold tracking-tight">Email</h1>
        {accounts.data && accounts.data.length > 1 && (
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
        )}
        {accounts.data?.length === 1 && <span className="text-sm text-muted-foreground">{account?.address}</span>}
        <div className="ml-auto flex items-center gap-2">
          <Button
            variant="ghost"
            size="sm"
            disabled={busy !== null || accountId === null}
            onClick={() =>
              run("overview", async () => {
                const data = await post<{ summary: string }>(`/api/email/accounts/${accountId}/summary`);
                setOverview(data.summary);
              })
            }
          >
            <Sparkles />
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
        </div>
      </div>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      {notice && (
        <p role="status" className="text-sm text-muted-foreground">
          {notice}
        </p>
      )}
      {overview && (
        <div className="rounded-xl border border-border bg-card p-3 text-sm">
          <div className="mb-1 flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="size-3.5 text-primary" aria-hidden="true" /> Luna&apos;s overview
            <button type="button" className="ml-auto underline-offset-2 hover:underline" onClick={() => setOverview(null)}>
              Hide
            </button>
          </div>
          <p className="whitespace-pre-wrap">{overview}</p>
        </div>
      )}

      <div className="grid min-h-0 flex-1 gap-3 md:grid-cols-[minmax(16rem,22rem)_1fr]">
        <section
          aria-label="Inbox"
          className={cn("min-h-0 overflow-auto rounded-xl border border-border bg-card", (reader || draft) && "hidden md:block")}
        >
          {inbox.isPending && <p className="p-4 text-sm text-muted-foreground">Loading your inbox...</p>}
          {inbox.isError && (
            <p role="alert" className="p-4 text-sm text-destructive">
              {inbox.error.message}
            </p>
          )}
          {inbox.data?.length === 0 && <p className="p-4 text-sm text-muted-foreground">Your inbox is empty.</p>}
          <ul>
            {inbox.data?.map((item) => (
              <li key={item.uid}>
                <button
                  type="button"
                  onClick={() => choose(item.uid)}
                  className={cn(
                    "flex w-full flex-col gap-0.5 border-b border-border px-3 py-2.5 text-left hover:bg-muted/60",
                    open === item.uid && "bg-muted",
                  )}
                >
                  <span className="flex items-center gap-2">
                    {item.unread && <span className="size-2 shrink-0 rounded-full bg-primary" aria-label="Unread" />}
                    <span className={cn("min-w-0 flex-1 truncate text-sm", item.unread && "font-semibold")}>{item.sender}</span>
                    <span className="shrink-0 text-xs text-muted-foreground">{when(item.date)}</span>
                  </span>
                  <span className={cn("truncate text-sm", item.unread ? "text-foreground" : "text-muted-foreground")}>
                    {item.subject}
                  </span>
                </button>
              </li>
            ))}
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
            <div className="space-y-3 rounded-xl border border-border bg-card p-4">
              <Button variant="ghost" size="sm" className="md:hidden" onClick={() => setOpen(null)}>
                <ArrowLeft />
                Inbox
              </Button>
              {message.isPending && <p className="text-sm text-muted-foreground">Opening...</p>}
              {message.isError && (
                <p role="alert" className="text-sm text-destructive">
                  {message.error.message}
                </p>
              )}
              {message.data && (
                <>
                  <div>
                    <h2 className="text-base font-semibold">{message.data.subject}</h2>
                    <p className="text-sm text-muted-foreground">
                      {message.data.sender} &lt;{message.data.sender_address}&gt;
                      {message.data.date && ` · ${new Date(message.data.date).toLocaleString()}`}
                    </p>
                    {message.data.attachments.length > 0 && (
                      <p className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
                        <Paperclip className="size-3.5" aria-hidden="true" />
                        {message.data.attachments.join(", ")}
                      </p>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 border-y border-border py-2">
                    <Button
                      variant="outline"
                      size="sm"
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
                    <Select value={tone} onValueChange={(value) => setTone(value as Tone)}>
                      <SelectTrigger className="h-8 w-36" aria-label="Tone">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="professional">Professional</SelectItem>
                        <SelectItem value="friendly">Friendly</SelectItem>
                        <SelectItem value="short">Short</SelectItem>
                      </SelectContent>
                    </Select>
                    <input
                      value={wish}
                      onChange={(e) => setWish(e.target.value)}
                      maxLength={1000}
                      placeholder="What to say (optional), e.g. yes, by Friday"
                      aria-label="What the reply should say"
                      className="h-8 min-w-48 flex-1 rounded-md border border-input bg-transparent px-2 text-sm hover:border-foreground/40"
                    />
                    <Button
                      size="sm"
                      disabled={busy !== null}
                      onClick={() =>
                        run("draft", async () => {
                          setDraft(await post<Draft>(`/api/email/accounts/${accountId}/messages/${open}/draft`, { tone, wish }));
                        })
                      }
                    >
                      <Reply />
                      {busy === "draft" ? "Writing..." : "Reply with Luna"}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
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
                  {summary && (
                    <div className="rounded-lg bg-muted/60 p-3 text-sm">
                      <p className="mb-1 text-xs text-muted-foreground">Luna&apos;s summary</p>
                      <p className="whitespace-pre-wrap">{summary}</p>
                    </div>
                  )}
                  <p className="whitespace-pre-wrap break-words text-sm leading-relaxed">{message.data.body || "(no text)"}</p>
                </>
              )}
            </div>
          ) : (
            <p className="p-4 text-sm text-muted-foreground">Pick a message to read it.</p>
          )}
        </section>
      </div>
      <p className="text-xs text-muted-foreground">
        Sum up and Reply with Luna send that email&apos;s text to your AI model. Venus never sends mail by itself.
      </p>
    </div>
  );
}
