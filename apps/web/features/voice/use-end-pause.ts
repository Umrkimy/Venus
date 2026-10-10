"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";

// Settings -> Voice: how long Venus waits after you stop talking (web and PC).
export const END_PAUSE_KEY = ["listening"];
export const DEFAULT_END_PAUSE_MS = 1500;

export type ListeningResponse = { end_pause_ms: number; mic: string };

export function useEndPause(): number {
  const query = useQuery({
    queryKey: END_PAUSE_KEY,
    queryFn: () => getJson<ListeningResponse>("/api/settings/listening"),
  });
  // Until Core answers (or if it can't), the usual 1.5 s.
  return query.data?.end_pause_ms ?? DEFAULT_END_PAUSE_MS;
}
