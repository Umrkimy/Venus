"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Inbox, PenLine, RefreshCw, Sparkles } from "lucide-react";
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
import { SignInNotice } from "@/features/calendar/reconnect-button";
import Composer, { type Draft } from "@/features/email/composer";
import { useEmailAccounts } from "@/features/email/email-accounts";
import InboxOverview, { type Overview } from "@/features/email/inbox-overview";
import { inboxQuery, load, post, type Category, type Message, type Summary } from "@/features/email/mail-api";
import MessageList from "@/features/email/message-list";
import MessageReader from "@/features/email/message-reader";
import type { Tone } from "@/features/email/tone-picker";
import { cn } from "@/lib/utils";

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
  const [tab, setTab] = useState<Category>("primary");

  const inbox = useQuery(inboxQuery(accountId));
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
  const unread = inbox.data?.filter((item) => item.unread && item.category === tab).length ?? 0;

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

      <SignInNotice />
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
        <MessageList
          inbox={inbox}
          account={account}
          tab={tab}
          onTab={setTab}
          open={open}
          onChoose={choose}
          hidden={reader || draft !== null}
        />

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
            <MessageReader
              message={message}
              summary={summary}
              tone={tone}
              onTone={setTone}
              wish={wish}
              onWish={setWish}
              busy={busy}
              onBack={() => setOpen(null)}
              onWriteReply={() =>
                run("draft", async () => {
                  compose(await post<Draft>(`/api/email/accounts/${accountId}/messages/${open}/draft`, { tone, wish }));
                })
              }
              onSumUp={() =>
                run("summary", async () => {
                  const data = await post<{ summary: string }>(`/api/email/accounts/${accountId}/messages/${open}/summary`);
                  setSummary(data.summary);
                })
              }
              onReplyMyself={(item) =>
                compose({
                  to: [item.sender_address],
                  cc: [],
                  subject: /^re:/i.test(item.subject) ? item.subject : `Re: ${item.subject}`,
                  body: "",
                  reply_to: open,
                })
              }
            />
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
