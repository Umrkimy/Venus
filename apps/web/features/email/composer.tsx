"use client";

import { Send, Sparkles, X } from "lucide-react";
import { useId, useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import TonePicker, { type Tone } from "@/features/email/tone-picker";
import { errorText } from "@/lib/error-text";

export type Draft = { to: string[]; cc: string[]; subject: string; body: string; reply_to: string | null };

const split = (text: string) =>
  text
    .split(/[,;\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);

// One "To: ____" line, like a mail app: the label sits inside the row.
function FieldRow({ label, children, id }: { label: string; children: React.ReactNode; id: string }) {
  return (
    <div className="flex items-center gap-3 border-b border-border px-4 focus-within:bg-muted/40">
      <label htmlFor={id} className="w-16 shrink-0 text-sm text-muted-foreground">
        {label}
      </label>
      {children}
    </div>
  );
}

const ROW_INPUT = "h-11 min-w-0 flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/70";

type Props = { accountId: string; draft: Draft; onClose: () => void; onSent: (to: string[]) => void };

// Writing or replying. Luna can fill the text in; only the owner's Send button sends it.
export default function Composer({ accountId, draft, onClose, onSent }: Props) {
  const ids = useId();
  const [to, setTo] = useState(draft.to.join(", "));
  const [cc, setCc] = useState(draft.cc.join(", "));
  const [showCc, setShowCc] = useState(draft.cc.length > 0);
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [wish, setWish] = useState("");
  const [tone, setTone] = useState<Tone>("professional");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState<"write" | "send" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const reply = draft.reply_to !== null;
  const byLuna = draft.body.length > 0;

  async function write() {
    setBusy("write");
    setError(null);
    try {
      const response = await fetch(`/api/email/accounts/${accountId}/draft`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: to.trim(), wish, tone }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data, "Luna couldn't write that."));
      setBody(data.body);
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Luna couldn't write that.");
    } finally {
      setBusy(null);
    }
  }

  async function send() {
    setConfirming(false);
    setBusy("send");
    setError(null);
    try {
      const response = await fetch(`/api/email/accounts/${accountId}/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ to: split(to), cc: split(cc), subject, body, reply_to: draft.reply_to }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data, "Couldn't send it."));
      onSent(split(to));
    } catch (exc) {
      setError(exc instanceof Error ? exc.message : "Couldn't send it.");
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-col overflow-hidden rounded-xl border border-border bg-card">
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <h2 className="text-base font-semibold">{reply ? "Reply" : "New email"}</h2>
        {byLuna && (
          <span className="flex items-center gap-1 rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
            <Sparkles className="size-3" aria-hidden="true" /> Written by Luna, check it before sending
          </span>
        )}
        <Button variant="ghost" size="icon-sm" className="ml-auto" aria-label="Close" onClick={onClose}>
          <X />
        </Button>
      </div>

      <FieldRow label="To" id={`${ids}-to`}>
        <input id={`${ids}-to`} value={to} onChange={(e) => setTo(e.target.value)} placeholder="name@example.com" className={ROW_INPUT} />
        {!showCc && (
          <button type="button" className="text-xs font-medium text-muted-foreground hover:text-foreground" onClick={() => setShowCc(true)}>
            Cc
          </button>
        )}
      </FieldRow>
      {showCc && (
        <FieldRow label="Cc" id={`${ids}-cc`}>
          <input id={`${ids}-cc`} value={cc} onChange={(e) => setCc(e.target.value)} placeholder="Optional" className={ROW_INPUT} />
        </FieldRow>
      )}
      <FieldRow label="Subject" id={`${ids}-subject`}>
        <input id={`${ids}-subject`} value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={300} className={ROW_INPUT} />
      </FieldRow>

      {!reply && (
        <div className="space-y-2 border-b border-border bg-muted/30 px-4 py-3">
          <div className="flex flex-wrap items-center gap-2">
            <p className="mr-auto flex items-center gap-1.5 text-sm font-semibold">
              <Sparkles className="size-4 text-primary" aria-hidden="true" /> Ask Luna to write it
            </p>
            <TonePicker value={tone} onChange={setTone} />
          </div>
          <div className="flex gap-2">
            <input
              value={wish}
              onChange={(e) => setWish(e.target.value)}
              maxLength={2000}
              placeholder="e.g. ask Dr. Aina for a 2-day extension on Assignment 2"
              aria-label="What the email should say"
              className="h-9 min-w-0 flex-1 rounded-md border border-input bg-background px-3 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring"
            />
            <Button type="button" variant="outline" disabled={busy !== null || !wish.trim()} onClick={write}>
              {busy === "write" ? "Writing..." : "Write"}
            </Button>
          </div>
        </div>
      )}

      <Textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        rows={14}
        aria-label="Message"
        placeholder="Write your message..."
        className="min-h-64 resize-y rounded-none border-0 px-4 py-3 text-[15px] leading-7 shadow-none focus-visible:ring-0"
      />

      {error && (
        <p role="alert" className="mx-4 mb-3 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex items-center gap-2 border-t border-border px-4 py-3">
        <Button disabled={busy !== null || !split(to).length || !body.trim()} onClick={() => setConfirming(true)}>
          <Send />
          {busy === "send" ? "Sending..." : "Send"}
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={busy !== null}>
          Discard
        </Button>
      </div>

      <AlertDialog open={confirming} onOpenChange={setConfirming}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Send this email?</AlertDialogTitle>
            <AlertDialogDescription>
              To {split(to).join(", ")}
              {subject ? `: "${subject}"` : ""}. Sent mail can&apos;t be taken back.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Keep editing</AlertDialogCancel>
            <AlertDialogAction onClick={send}>Send</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
