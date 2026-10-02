"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type Personality = {
  id: string;
  name: string;
  text: string;
  active: boolean;
  updated_at: string;
};

// Same limits as Core, so the form stops you before Core would.
export const NAME_LIMIT = 40;
export const TEXT_LIMIT = 4000;

export function usePersonalities() {
  return useQuery({
    queryKey: ["personalities"],
    queryFn: () => getJson<Personality[]>("/api/personalities"),
  });
}

// Each action returns null or false when it failed, and `error` says why.
export function usePersonalityActions() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  async function send(url: string, init: RequestInit, failure: string) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (response.status === 409) {
        // e.g. "Switch personality first": Core's own words say what to do.
        const data = await response.json();
        setError(data.detail);
        return null;
      }
      if (!response.ok) {
        setError(failure);
        return null;
      }
      await queryClient.invalidateQueries({ queryKey: ["personalities"] });
      return response;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return null;
    }
  }

  function jsonRequest(method: string, body: object): RequestInit {
    return {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    };
  }

  async function create(name: string, text: string): Promise<Personality | null> {
    const response = await send(
      "/api/personalities",
      jsonRequest("POST", { name, text }),
      "Couldn't create that personality.",
    );
    return response ? response.json() : null;
  }

  async function update(id: string, name: string, text: string) {
    const response = await send(
      `/api/personalities/${id}`,
      jsonRequest("PATCH", { name, text }),
      "Couldn't save that personality.",
    );
    return response !== null;
  }

  async function activate(id: string) {
    const response = await send(
      `/api/personalities/${id}`,
      jsonRequest("PATCH", { active: true }),
      "Couldn't switch personality.",
    );
    return response !== null;
  }

  async function remove(id: string) {
    const response = await send(
      `/api/personalities/${id}`,
      { method: "DELETE" },
      "Couldn't delete that personality.",
    );
    return response !== null;
  }

  return { error, create, update, activate, remove };
}
