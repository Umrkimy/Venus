"use client";

import { useParams } from "next/navigation";

import { SavedChat } from "@/features/chat/chat-panel";

export default function ChatPage() {
  const { id } = useParams<{ id: string }>();
  // key: opening another chat starts a fresh card instead of reusing state.
  return <SavedChat key={id} conversationId={id} />;
}
