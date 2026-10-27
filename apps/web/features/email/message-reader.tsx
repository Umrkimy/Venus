"use client";

import type { UseQueryResult } from "@tanstack/react-query";
import { ArrowLeft, Paperclip, Reply, Sparkles } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import type { Message } from "@/features/email/mail-api";
import MailBody from "@/features/email/mail-body";
import TonePicker, { SenderAvatar, type Tone } from "@/features/email/tone-picker";

type Props = {
  message: UseQueryResult<Message>;
  summary: string | null;
  tone: Tone;
  onTone: (tone: Tone) => void;
  wish: string;
  onWish: (wish: string) => void;
  busy: string | null;
  onBack: () => void;
  onWriteReply: () => void;
  onSumUp: () => void;
  onReplyMyself: (message: Message) => void;
};

// One open message, with Luna's summary and reply help under it.
export default function MessageReader({
  message,
  summary,
  tone,
  onTone,
  wish,
  onWish,
  busy,
  onBack,
  onWriteReply,
  onSumUp,
  onReplyMyself,
}: Props) {
  return (
    <article className="rounded-xl border border-border bg-card">
      <div className="space-y-4 p-4 sm:p-5">
        <Button variant="ghost" size="sm" className="-ml-2 md:hidden" onClick={onBack}>
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
            <TonePicker value={tone} onChange={onTone} />
          </div>
          <Textarea
            value={wish}
            onChange={(e) => onWish(e.target.value)}
            maxLength={1000}
            rows={2}
            placeholder="What should it say? e.g. yes, I'll submit by Friday (optional)"
            aria-label="What the reply should say"
            className="resize-none bg-background"
          />
          <div className="flex flex-wrap items-center gap-2">
            <Button disabled={busy !== null} onClick={onWriteReply}>
              <Reply />
              {busy === "draft" ? "Writing..." : "Write reply"}
            </Button>
            <Button variant="outline" disabled={busy !== null} onClick={onSumUp}>
              <Sparkles />
              {busy === "summary" ? "Reading..." : "Sum up"}
            </Button>
            <Button variant="ghost" className="ml-auto" onClick={() => onReplyMyself(message.data!)}>
              Reply myself
            </Button>
          </div>
        </div>
      )}
    </article>
  );
}
