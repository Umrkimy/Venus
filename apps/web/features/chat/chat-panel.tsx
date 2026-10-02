"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import ChatBox, { type ChatMessage } from "./chat-box";
import { getJson } from "@/lib/get-json";
import { useNodes } from "@/lib/use-nodes";

type CommandStatus = { command_id: string; status: string; detail?: string };
type SavedConversation = {
  id: string;
  title: string;
  messages: { role: "user" | "assistant"; content: string }[];
};

// Once a command reaches one of these, it never changes again.
const FINAL_STATUSES = ["succeeded", "failed", "denied", "expired", "unknown"];

const STATUS_TEXT: Record<string, string> = {
  dispatched: "Sent to your PC…",
  succeeded: "Opened.",
  failed: "Your PC couldn't open it.",
  denied: "Denied.",
  expired: "Expired before you decided.",
  unknown: "No answer from your PC.",
};

// The see-through card in front of the scene.
function ChatCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="mx-auto flex min-h-0 w-full max-w-2xl flex-1 flex-col px-4 pb-4">
      <section className="flex min-h-0 flex-1 flex-col rounded-2xl border border-border/60 bg-card text-card-foreground shadow-lg backdrop-blur-xl">
        {children}
      </section>
    </div>
  );
}

// Loader for /chat/<id>: waits for the saved lines, then draws the chat
// with them (useState only takes its start value on the first draw).
export function SavedChat({ conversationId }: { conversationId: string }) {
  const saved = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () =>
      getJson<SavedConversation>(`/api/conversations/${conversationId}`),
    refetchOnMount: "always",
  });

  if (saved.isError) {
    return (
      <ChatCard>
        <div role="alert" className="m-auto text-center">
          <p className="text-destructive">This chat doesn&apos;t exist.</p>
          <Button asChild variant="outline" className="mt-3">
            <Link href="/">Start a new chat</Link>
          </Button>
        </div>
      </ChatCard>
    );
  }

  // Wait for this visit's answer, not an older cached copy.
  if (!saved.isFetchedAfterMount || !saved.data) {
    return (
      <ChatCard>
        <div role="status" className="m-auto">
          <span className="sr-only">Loading chat</span>
          <div className="h-5 w-40 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
        </div>
      </ChatCard>
    );
  }

  return (
    <ChatPanel
      conversationId={conversationId}
      initialMessages={saved.data.messages.map((m) => ({
        from: m.role === "user" ? "you" : "venus",
        text: m.content,
      }))}
    />
  );
}

type ChatPanelProps = {
  conversationId: string | null;
  initialMessages: ChatMessage[];
};

export default function ChatPanel({
  conversationId: startId,
  initialMessages,
}: ChatPanelProps) {
  const queryClient = useQueryClient();
  const [conversationId, setConversationId] = useState(startId);
  const [commandId, setCommandId] = useState<string | null>(null);
  const [targetName, setTargetName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  // Venus has one PC for now: the chat talks to the first one online.
  const nodes = useNodes();
  const deviceId = nodes.data?.device_ids[0];

  const command = useQuery({
    queryKey: ["command", commandId],
    queryFn: () => getJson<CommandStatus>(`/api/commands/${commandId}`),
    enabled: commandId !== null,
    refetchInterval: (query) =>
      FINAL_STATUSES.includes(query.state.data?.status ?? "") ? false : 1000,
  });

  const status = command.data?.status;
  const inFlight = commandId !== null && !FINAL_STATUSES.includes(status ?? "");

  async function post(url: string, body?: object) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await response.json();
      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Something went wrong.",
        );
        return null;
      }
      return data;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function chat(text: string) {
    if (!deviceId) return;
    // Show your message at once; the updater keeps both adds below.
    setMessages((old) => [...old, { from: "you", text }]);
    // No id yet means Core starts a new conversation and sends its id back.
    // Core reads the earlier lines itself, so only the new one is sent.
    const data = await post(`/api/nodes/${encodeURIComponent(deviceId)}/chat`, {
      message: text,
      conversation_id: conversationId ?? undefined,
    });
    if (!data) return;
    if (conversationId === null) {
      setConversationId(data.conversation_id);
      // Change the address without reloading, so this card keeps its state.
      window.history.replaceState(null, "", `/chat/${data.conversation_id}`);
    }
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
    if (data.type === "reply") {
      setMessages((old) => [...old, { from: "venus", text: data.reply }]);
      return;
    }
    // A command: Venus asks before opening anything (unless Full mode).
    setMessages((old) => [
      ...old,
      { from: "venus", text: `On it: ${data.label}` },
    ]);
    setTargetName(data.label);
    setCommandId(data.command_id);
  }

  async function decide(approved: boolean) {
    if (commandId === null) return;
    await post(`/api/commands/${commandId}/approval`, { approved });
    await command.refetch();
  }

  return (
    <ChatCard>
      <ChatBox
        disabled={busy || inFlight || !deviceId}
        placeholder={
          deviceId
            ? "Ask Venus anything, e.g. open spotify"
            : "Your PC is offline. Start Venus Node to chat."
        }
        messages={messages}
        onSend={chat}
      />

      <div aria-live="polite" className="empty:hidden px-4 pb-3">
        {status === "awaiting_approval" && (
          <div className="rounded-xl border border-border p-4">
            <p className="break-all">Open {targetName} on this PC?</p>
            <div className="mt-3 flex gap-2">
              <Button onClick={() => decide(true)} disabled={busy}>
                Approve
              </Button>
              <Button
                variant="outline"
                onClick={() => decide(false)}
                disabled={busy}
              >
                Deny
              </Button>
            </div>
          </div>
        )}

        {status && status !== "awaiting_approval" && (
          <p role="status" className="text-sm">
            {STATUS_TEXT[status] ?? status}
          </p>
        )}

        {command.isError && (
          <p role="alert" className="text-sm text-destructive">
            Lost track of this command.
          </p>
        )}

        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </ChatCard>
  );
}
