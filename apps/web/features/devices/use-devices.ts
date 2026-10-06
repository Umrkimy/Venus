"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type Device = {
  id: string;
  name: string;
  // Empty until a Node first connects with the token.
  device_id: string | null;
  created_at: string;
  last_seen_at: string | null;
  revoked_at: string | null;
  // The PC from apps/core/.env: it can't be revoked here.
  main: boolean;
  connected: boolean;
};

// Same limit as Core.
export const NAME_LIMIT = 60;

export function useDevices() {
  return useQuery({
    queryKey: ["devices"],
    queryFn: () => getJson<Device[]>("/api/devices"),
    // "Connected" changes when a PC starts or stops.
    refetchInterval: 10_000,
  });
}

export function useDeviceActions() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  // Resolves to Core's answer, or null when it failed.
  async function send(url: string, init: RequestInit, failure: string) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        setError(failure);
        return null;
      }
      await queryClient.invalidateQueries({ queryKey: ["devices"] });
      // A delete answers 204 with no body.
      return response.status === 204 ? {} : response.json();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return null;
    }
  }

  // Resolves to the new token, which Core shows only this once.
  async function create(name: string): Promise<string | null> {
    const created = await send(
      "/api/devices",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name }),
      },
      "Couldn't add that device.",
    );
    return created?.token ?? null;
  }

  async function revoke(id: string) {
    const revoked = await send(
      `/api/devices/${id}/revoke`,
      { method: "POST" },
      "Couldn't revoke that device.",
    );
    return revoked !== null;
  }

  // Only revoked devices can go; Core refuses the others.
  async function remove(id: string) {
    const response = await send(
      `/api/devices/${id}`,
      { method: "DELETE" },
      "Couldn't delete that device.",
    );
    return response !== null;
  }

  return { error, create, revoke, remove };
}
