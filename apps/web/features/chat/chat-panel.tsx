"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState, type ReactNode } from "react";

import { Button } from "@/components/ui/button";
import { isFinal, useCommandStatus, type ChatAction } from "./action-card";
import ChatBox, { type ChatMessage } from "./chat-box";
import { useSpeaker } from "./use-speaker";
import { getJson } from "@/lib/get-json";
import { useListenOn } from "@/features/voice/listen-store";
import { useHandsFree } from "@/features/voice/use-hands-free";
import { useFrontTab, useVoiceState, type VoiceStateName } from "@/features/voice/use-voice-state";
import { POLL_MS, VOICE_POLL_MS } from "@/lib/poll";
import { useNodes } from "@/lib/use-nodes";

type SavedMessage = {
  role: "user" | "assistant";
  content: string;
  actions?: ChatAction[];
};

type SavedConversation = {
  id: string;
  title: string;
  messages: SavedMessage[];
};

function toChatMessage(m: SavedMessage): ChatMessage {
  return { from: m.role === "user" ? "you" : "venus", text: m.content, actions: m.actions };
}

function getConversation(id: string) {
  return getJson<SavedConversation>(`/api/conversations/${id}`);
}

// Full-size and see-through, so the scene (later the 3D Venus) shows behind the chat.
function ChatCard({ children }: { children: React.ReactNode }) {
  return <section className="flex min-h-0 w-full flex-1 flex-col">{children}</section>;
}

// Loader for /chat/<id>: waits for the saved lines, then draws the chat
// with them (useState only takes its start value on the first draw).
export function SavedChat({ conversationId }: { conversationId: string }) {
  const saved = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId),
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
      initialMessages={saved.data.messages.map(toChatMessage)}
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
  // From typing a line until Luna's reply is on screen.
  const [sending, setSending] = useState(false);
  // Your line arrived from the PC (voice) and Luna's reply hasn't yet.
  const [thinkingElsewhere, setThinkingElsewhere] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const speaker = useSpeaker();
  // A voice turn on the PC that goes into this chat.
  const front = useFrontTab();
  const voice = useVoiceState(front);
  // Stop pressed (or said) while Luna's answer was on its way: don't speak it.
  const dropReplyRef = useRef(false);
  const voiceHere =
    voice !== undefined && voice.state !== "idle" && voice.conversation_id === conversationId;

  // Lines added elsewhere (a voice turn on the PC) appear without a reload,
  // quicker while you're talking so your words show right after you say them.
  const synced = useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: () => getConversation(conversationId!),
    enabled: conversationId !== null,
    refetchInterval: voiceHere ? VOICE_POLL_MS : POLL_MS,
  });
  const savedLines = synced.data?.messages;
  // Not while sending: the saved copy of our own line would show twice.
  if (savedLines && !sending && savedLines.length > messages.length) {
    const added = savedLines.slice(messages.length).map(toChatMessage);
    setMessages([...messages, ...added]);
    setThinkingElsewhere(added[added.length - 1].from === "you");
  }

  // If her reply never comes (Core error), don't show the dots forever.
  useEffect(() => {
    if (!thinkingElsewhere) return;
    const timer = setTimeout(() => setThinkingElsewhere(false), 60_000);
    return () => clearTimeout(timer);
  }, [thinkingElsewhere]);

  // Venus has one PC for now: the chat talks to the first one online.
  const nodes = useNodes();
  const deviceId = nodes.data?.device_ids[0];

  function stopVoice() {
    speaker.stop();
    if (sending) dropReplyRef.current = true;
  }

  // Hands-free: the browser mic listens while this tab is in front.
  const listenOn = useListenOn();
  const handsFree = useHandsFree({
    enabled: listenOn && front && deviceId !== undefined,
    busy: sending || speaker.speaking !== null,
    onHeard: (text) => void chat(text),
    onStop: stopVoice,
  });
  let localVoice: VoiceStateName | null = null;
  if (handsFree.phase !== "off") {
    if (speaker.speaking !== null) localVoice = "speaking";
    else if (sending || handsFree.phase === "transcribing") localVoice = "thinking";
    else if (handsFree.phase === "recording") localVoice = "listening";
    else localVoice = "idle";
  }

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
    setSending(true);
    try {
      await send(deviceId, text);
    } finally {
      setSending(false);
    }
  }

  async function send(deviceId: string, text: string) {
    // Luna's reply lands after your line; the input is locked until then.
    const replyId = messages.length + 1;
    dropReplyRef.current = false;
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
        reveal: data.reply && speaker.on ? "voice" : "type",
      },
    ]);
    // Only Luna's own words; the "On it" stand-in isn't worth a voice call.
    if (data.reply && !dropReplyRef.current) speaker.speak(replyId, data.reply);
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
        speaker={speaker}
        emptyState={emptyState}
        thinking={sending || thinkingElsewhere}
        listening={(voiceHere && voice.state === "listening") || handsFree.phase === "recording"}
        localVoice={localVoice}
        onStopVoice={stopVoice}
      />

      <div aria-live="polite" className="empty:hidden mx-auto w-full max-w-3xl px-4 pb-3">
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
        {handsFree.error && (
          <p role="alert" className="text-sm text-destructive">
            {handsFree.error}
          </p>
        )}
      </div>
    </ChatCard>
  );
}
