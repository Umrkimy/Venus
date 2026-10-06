"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type BrowserSession = {
  id: string;
  user_agent: string | null;
  created_at: string;
  last_seen_at: string | null;
  // True for the browser showing this page.
  current: boolean;
};

export function useSessions() {
  return useQuery({
    queryKey: ["sessions"],
    queryFn: () => getJson<BrowserSession[]>("/api/auth/sessions"),
  });
}

export function useSessionActions() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  async function send(url: string, init: RequestInit) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        setError("Couldn't sign that out.");
        return false;
      }
      await queryClient.invalidateQueries({ queryKey: ["sessions"] });
      return true;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return false;
    }
  }

  function signOut(id: string) {
    return send(`/api/auth/sessions/${id}`, { method: "DELETE" });
  }

  function signOutOthers() {
    return send("/api/auth/sessions/sign-out-others", { method: "POST" });
  }

  return { error, signOut, signOutOthers };
}
