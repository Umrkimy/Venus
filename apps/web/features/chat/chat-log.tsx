"use client";

import { ScrollText } from "lucide-react";
import { useRef } from "react";

import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import ActionCard from "./action-card";
import type { ChatMessage, Speaker } from "./chat-box";
import ReplayButton from "./replay-button";

// One message in the log, the chat-app way: your lines right, hers left.
function LogLine({ message, index, speaker }: { message: ChatMessage; index: number; speaker: Speaker }) {
  return (
    <li
      className={
        message.from === "you"
          ? "ml-auto w-fit max-w-[85%] rounded-2xl bg-foreground/10 px-4 py-2 break-words whitespace-pre-wrap"
          : "group max-w-[85%] break-words whitespace-pre-wrap"
      }
    >
      <span className="sr-only">{message.from === "you" ? "You: " : "Venus: "}</span>
      {message.actions && message.actions.length > 0 && (
        <ActionCard actions={message.actions} startOpen={false} />
      )}
      {message.text}
      {message.from === "venus" && message.text && (
        <ReplayButton
          onReplay={() => speaker.replay(index, message.text)}
          playing={speaker.speaking?.id === index}
        />
      )}
    </li>
  );
}

// Every line of this chat, in a panel from the right.
export default function ChatLog({ messages, speaker }: { messages: ChatMessage[]; speaker: Speaker }) {
  const endRef = useRef<HTMLLIElement>(null);

  return (
    <Sheet
      onOpenChange={(open) => {
        // Open at the newest line, once the panel is drawn.
        if (open) setTimeout(() => endRef.current?.scrollIntoView({ block: "end" }));
      }}
    >
      <SheetTrigger asChild>
        <Button
          type="button"
          variant="ghost"
          size="sm"
          disabled={messages.length === 0}
          className="pointer-events-auto rounded-full bg-background/40 backdrop-blur-md"
        >
          <ScrollText />
          Log
        </Button>
      </SheetTrigger>
      <SheetContent className="w-full sm:max-w-lg">
        <SheetHeader>
          <SheetTitle>Log</SheetTitle>
          <SheetDescription>Everything said in this chat.</SheetDescription>
        </SheetHeader>
        <ul role="log" className="min-h-0 flex-1 space-y-5 overflow-y-auto px-4 pb-4">
          {/* Messages are only ever added, so the position is a safe key. */}
          {messages.map((message, index) => (
            <LogLine key={index} message={message} index={index} speaker={speaker} />
          ))}
          <li ref={endRef} aria-hidden="true" />
        </ul>
      </SheetContent>
    </Sheet>
  );
}
