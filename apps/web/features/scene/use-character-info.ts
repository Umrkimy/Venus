"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";
import type { MoveInfo } from "./uploaded-moves";

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

// Your uploaded .vrma moves (Core keeps them; never in git). Empty = coded moves only.
export function useCharacterMoves() {
  return useQuery({
    queryKey: ["character", "animations"],
    queryFn: () => getJson<MoveInfo[]>("/api/character/animations"),
    retry: false,
  });
}
