"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Brain,
  Check,
  ChevronRight,
  Clock,
  LoaderCircle,
  Wrench,
  X,
} from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { getJson } from "@/lib/get-json";

// What Venus did for one reply, as Core sends it.
export type ChatAction =
  | { kind: "command"; command_id: string; label: string }
  | { kind: "memory"; text: string };

type CommandStatus = { command_id: string; status: string; detail?: string };

// Once a command reaches one of these, it never changes again.
const FINAL_STATUSES = ["succeeded", "failed", "denied", "expired", "unknown"];

const STATUS_TEXT: Record<string, string> = {
  awaiting_approval: "Waiting for you",
  dispatched: "Sending to your PC…",
  succeeded: "Opened",
  failed: "Your PC couldn't open it",
  denied: "Denied",
  expired: "Expired",
  unknown: "No answer from your PC",
};

// One cache entry per command: the card and the chat input share it.
export function useCommandStatus(commandId: string | null, enabled = true) {
  return useQuery({
    queryKey: ["command", commandId],
    queryFn: () => getJson<CommandStatus>(`/api/commands/${commandId}`),
    enabled: enabled && commandId !== null,
    refetchInterval: (query) =>
      isFinal(query.state.data?.status) ? false : 1000,
  });
}

export function isFinal(status: string | undefined) {
  return FINAL_STATUSES.includes(status ?? "");
}

type ActionCardProps = {
  actions: ChatAction[];
  // Started open in this visit, so Approve is in view; saved ones start closed.
  startOpen: boolean;
};

export default function ActionCard({ actions, startOpen }: ActionCardProps) {
  const [open, setOpen] = useState(startOpen);
  const count = actions.length;

  return (
    <details
      open={open}
      onToggle={(event) => setOpen(event.currentTarget.open)}
      className="group mb-2 w-full max-w-sm rounded-xl border border-border/60 bg-background/40"
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 rounded-xl px-3 py-2 text-sm text-muted-foreground select-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none [&::-webkit-details-marker]:hidden">
        <Wrench className="size-4" aria-hidden="true" />
        <span>
          Used {count} {count === 1 ? "tool" : "tools"}
        </span>
        <ChevronRight
          className="ml-auto size-4 transition-transform group-open:rotate-90"
          aria-hidden="true"
        />
      </summary>
      <ul className="space-y-3 border-t border-border/60 px-3 py-3">
        {/* Actions never change order, so the position is a safe key. */}
        {actions.map((action, index) => (
          <li key={index}>
            {action.kind === "command" ? (
              <CommandRow
                commandId={action.command_id}
                label={action.label}
                // Old chats only ask Core once you look inside.
                watch={open}
              />
            ) : (
              <MemoryRow text={action.text} />
            )}
          </li>
        ))}
      </ul>
    </details>
  );
}

function CommandRow({
  commandId,
  label,
  watch,
}: {
  commandId: string;
  label: string;
  watch: boolean;
}) {
  const command = useCommandStatus(commandId, watch);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const status = command.data?.status;

  async function decide(approved: boolean) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/commands/${commandId}/approval`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ approved }),
      });
      if (!response.ok) setError("Couldn't send your answer.");
      await command.refetch();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-2 text-sm">
      <div className="flex items-center gap-2">
        <StatusIcon status={status} />
        <span className="min-w-0 flex-1 break-all">Open {label}</span>
        <span aria-live="polite" className="text-xs text-muted-foreground">
          {status ? (STATUS_TEXT[status] ?? status) : "Checking…"}
        </span>
      </div>

      {status === "awaiting_approval" && (
        <div className="flex gap-2 pl-6">
          <Button size="sm" onClick={() => decide(true)} disabled={busy}>
            Approve
          </Button>
          <Button
            size="sm"
            variant="outline"
            onClick={() => decide(false)}
            disabled={busy}
          >
            Deny
          </Button>
        </div>
      )}

      {command.isError && (
        <p role="alert" className="pl-6 text-destructive">
          Lost track of this command.
        </p>
      )}
      {error && (
        <p role="alert" className="pl-6 text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}

function StatusIcon({ status }: { status: string | undefined }) {
  if (status === "succeeded") {
    return <Check className="size-4 text-primary" aria-hidden="true" />;
  }
  if (status === "awaiting_approval") {
    return <Clock className="size-4 text-muted-foreground" aria-hidden="true" />;
  }
  if (isFinal(status)) {
    return <X className="size-4 text-destructive" aria-hidden="true" />;
  }
  return (
    <LoaderCircle
      className="size-4 text-muted-foreground motion-safe:animate-spin"
      aria-hidden="true"
    />
  );
}

function MemoryRow({ text }: { text: string }) {
  return (
    <div className="flex items-start gap-2 text-sm">
      <Brain className="mt-0.5 size-4 text-primary" aria-hidden="true" />
      <div className="min-w-0">
        <p className="text-xs text-muted-foreground">Saved to memory</p>
        <p className="break-words">{text}</p>
      </div>
    </div>
  );
}
