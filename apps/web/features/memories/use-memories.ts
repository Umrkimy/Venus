"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type Memory = {
  id: string;
  text: string;
  created_at: string;
};

// Same limit as Core, so the form stops you before Core would.
export const TEXT_LIMIT = 300;

// Core sends the newest fact first.
export function useMemories() {
  return useQuery({
    queryKey: ["memories"],
    queryFn: () => getJson<Memory[]>("/api/memories"),
  });
}

// Each action returns false when it failed, and `error` says why.
export function useMemoryActions() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  async function send(url: string, init: RequestInit, failure: string) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        setError(failure);
        return false;
      }
      await queryClient.invalidateQueries({ queryKey: ["memories"] });
      return true;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return false;
    }
  }

  function jsonRequest(method: string, text: string): RequestInit {
    return {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    };
  }

  function create(text: string) {
    return send("/api/memories", jsonRequest("POST", text), "Couldn't save that memory.");
  }

  function update(id: string, text: string) {
    return send(
      `/api/memories/${id}`,
      jsonRequest("PATCH", text),
      "Couldn't save that memory.",
    );
  }

  function remove(id: string) {
    return send(
      `/api/memories/${id}`,
      { method: "DELETE" },
      "Couldn't delete that memory.",
    );
  }

  return { error, create, update, remove };
}
