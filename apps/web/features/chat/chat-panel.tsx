"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { isFinal, useCommandStatus, type ChatAction } from "./action-card";
import ChatBox, { type ChatMessage } from "./chat-box";
import { getJson } from "@/lib/get-json";
import { useNodes } from "@/lib/use-nodes";

type SavedConversation = {
  id: string;
  title: string;
  messages: {
    role: "user" | "assistant";
    content: string;
    actions?: ChatAction[];
  }[];
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
        actions: m.actions,
      }))}
    />
  );
}

type ChatPanelProps = {
  conversationId: string | null;
  initialMessages: ChatMessage[];
  // A new chat started here is created inside this project.
  projectId?: string;
  emptyState?: ReactNode;
};

export default function ChatPanel({
  conversationId: startId,
  initialMessages,
  projectId,
  emptyState,
}: ChatPanelProps) {
  const queryClient = useQueryClient();
  const [conversationId, setConversationId] = useState(startId);
  // The newest command: the input stays locked until it is finished.
  const [commandId, setCommandId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  // Venus has one PC for now: the chat talks to the first one online.
  const nodes = useNodes();
  const deviceId = nodes.data?.device_ids[0];

  const command = useCommandStatus(commandId);
  const inFlight =
    commandId !== null && !command.isError && !isFinal(command.data?.status);

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
      project_id: conversationId === null ? projectId : undefined,
    });
    if (!data) return;
    if (conversationId === null) {
      setConversationId(data.conversation_id);
      // Change the address without reloading, so this card keeps its state.
      window.history.replaceState(null, "", `/chat/${data.conversation_id}`);
    }
    queryClient.invalidateQueries({ queryKey: ["conversations"] });
    setMessages((old) => [
      ...old,
      {
        from: "venus",
        text: data.reply ?? `On it: ${data.label}`,
        actions: data.actions,
        live: true,
      },
    ]);
    // A command: Venus asks before opening anything (unless Full mode);
    // its card holds Approve and Deny.
    if (data.type === "command") setCommandId(data.command_id);
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
        emptyState={emptyState}
      />

      <div aria-live="polite" className="empty:hidden px-4 pb-3">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </div>
    </ChatCard>
  );
}
