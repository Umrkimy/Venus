"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";

// Your own uploaded model, if any (Core keeps it; never in git).
export type CharacterInfo =
  | { custom: false }
  | { custom: true; name: string; size: number; uploaded_at: string };

export function useCharacterInfo() {
  return useQuery({
    queryKey: ["character"],
    queryFn: () => getJson<CharacterInfo>("/api/character"),
    // Signed out (401) just means the template; no point asking again.
    retry: false,
  });
}
