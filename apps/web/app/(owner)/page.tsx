"use client";

import ChatPanel from "@/features/chat/chat-panel";
import { useNewChat } from "@/features/chat/new-chat";

// "/" is always a new chat; the first reply moves the address to /chat/<id>.
export default function Home() {
  const { count } = useNewChat();
  return <ChatPanel key={count} conversationId={null} initialMessages={[]} />;
}
