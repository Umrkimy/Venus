"use client";

import { useQueryClient } from "@tanstack/react-query";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import { useNewChat } from "@/features/chat/new-chat";

// Archive, unarchive and delete for the sidebar's chat rows.
export function useChatActions() {
  const queryClient = useQueryClient();
  const pathname = usePathname();
  const router = useRouter();
  const { startNewChat } = useNewChat();
  const [error, setError] = useState<string | null>(null);

  // A deleted or archived chat shouldn't stay on screen: go to a fresh chat.
  function leaveIfOpen(id: string) {
    if (pathname === `/chat/${id}`) {
      startNewChat();
      router.push("/");
    }
  }

  async function send(url: string, init: RequestInit, failure: string) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        setError(failure);
        return false;
      }
      // ["conversations"] also matches ["conversations", "archived"].
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
      return true;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return false;
    }
  }

  async function setArchived(id: string, archived: boolean) {
    const done = await send(
      `/api/conversations/${id}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived }),
      },
      archived ? "Couldn't archive that chat." : "Couldn't unarchive that chat.",
    );
    if (done && archived) leaveIfOpen(id);
  }

  async function deleteChat(id: string) {
    // 204 has an empty body, so send() never reads response.json().
    const done = await send(
      `/api/conversations/${id}`,
      { method: "DELETE" },
      "Couldn't delete that chat.",
    );
    if (done) {
      queryClient.removeQueries({ queryKey: ["conversation", id] });
      leaveIfOpen(id);
    }
  }

  return { error, setArchived, deleteChat };
}
