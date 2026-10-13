import { DEMO, DEMO_CHAT_IDS } from "@/features/demo/demo-mode";
import ChatPage from "./chat-page";

// Real Venus makes each chat's page when it's opened. The static demo can't,
// so it builds a page for each of its chat ids up front.
export function generateStaticParams() {
  return DEMO ? DEMO_CHAT_IDS.map((id) => ({ id })) : [];
}

export default function Page() {
  return <ChatPage />;
}
