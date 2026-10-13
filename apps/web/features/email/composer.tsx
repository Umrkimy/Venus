"use client";

import { Send, Sparkles, X } from "lucide-react";
import { useState } from "react";

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
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";

export type Tone = "professional" | "friendly" | "short";
export type Draft = { to: string[]; cc: string[]; subject: string; body: string; reply_to: string | null };

const split = (text: string) =>
  text
    .split(/[,;\s]+/)
    .map((part) => part.trim())
    .filter(Boolean);

function errorText(data: { detail?: unknown }, fallback: string) {
  const first = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : fallback;
}

type Props = { accountId: string; draft: Draft; onClose: () => void; onSent: (to: string[]) => void };

// Writing or replying. Luna can fill the text in; only the owner's Send button sends it.
export default function Composer({ accountId, draft, onClose, onSent }: Props) {
  const [to, setTo] = useState(draft.to.join(", "));
  const [cc, setCc] = useState(draft.cc.join(", "));
  const [subject, setSubject] = useState(draft.subject);
  const [body, setBody] = useState(draft.body);
  const [wish, setWish] = useState("");
  const [tone, setTone] = useState<Tone>("professional");
  const [confirming, setConfirming] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reply = draft.reply_to !== null;

  async function write() {
    setBusy(true);
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
      setBusy(false);
    }
  }

  async function send() {
    setConfirming(false);
    setBusy(true);
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
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3 rounded-xl border border-border bg-card p-4">
      <div className="flex items-center gap-2">
        <h2 className="text-base font-semibold">{reply ? "Reply" : "New email"}</h2>
        {draft.body && <span className="text-xs text-muted-foreground">Written by Luna: read it before sending.</span>}
        <Button variant="ghost" size="icon-sm" className="ml-auto" aria-label="Close" onClick={onClose}>
          <X />
        </Button>
      </div>
      <label className={LABEL_CLASS}>
        To
        <Input value={to} onChange={(e) => setTo(e.target.value)} placeholder="name@example.com" className={FIELD_HOVER} />
      </label>
      <label className={LABEL_CLASS}>
        Cc
        <Input value={cc} onChange={(e) => setCc(e.target.value)} placeholder="Optional" className={FIELD_HOVER} />
      </label>
      <label className={LABEL_CLASS}>
        Subject
        <Input value={subject} onChange={(e) => setSubject(e.target.value)} maxLength={300} className={FIELD_HOVER} />
      </label>
      {!reply && (
        <div className="flex flex-wrap items-end gap-2 rounded-lg bg-muted/50 p-2">
          <label className="min-w-48 flex-1 text-sm font-medium">
            Ask Luna to write it
            <Input
              value={wish}
              onChange={(e) => setWish(e.target.value)}
              maxLength={2000}
              placeholder="e.g. ask Dr. Aina for a 2-day extension on Assignment 2"
              className={FIELD_HOVER}
            />
          </label>
          <select
            value={tone}
            onChange={(e) => setTone(e.target.value as Tone)}
            aria-label="Tone"
            className="h-9 rounded-md border border-input bg-transparent px-2 text-sm"
          >
            <option value="professional">Professional</option>
            <option value="friendly">Friendly</option>
            <option value="short">Short</option>
          </select>
          <Button type="button" variant="outline" disabled={busy || !wish.trim()} onClick={write}>
            <Sparkles />
            Write
          </Button>
        </div>
      )}
      <label className={LABEL_CLASS}>
        Message
        <Textarea value={body} onChange={(e) => setBody(e.target.value)} rows={12} className="mt-1.5" />
      </label>
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
      <div className="flex items-center gap-2">
        <Button disabled={busy || !split(to).length || !body.trim()} onClick={() => setConfirming(true)}>
          <Send />
          {busy ? "Sending..." : "Send"}
        </Button>
        <Button variant="ghost" onClick={onClose} disabled={busy}>
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
