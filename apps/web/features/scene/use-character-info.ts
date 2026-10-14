"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";
import type { MoveInfo } from "./uploaded-moves";

// Your own uploaded model, if any (Core keeps it; never in git).
export type CharacterInfo =
  | { custom: false }
  | { custom: true; id: number; name: string; size: number; uploaded_at: string };

// Every model you uploaded; the active one is the one Venus shows.
export type CharacterModelInfo = {
  id: number;
  name: string;
  size: number;
  uploaded_at: string;
  active: boolean;
};

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

export function useCharacterModels() {
  return useQuery({
    queryKey: ["character", "models"],
    queryFn: () => getJson<CharacterModelInfo[]>("/api/character/models"),
    retry: false,
  });
}

// Your uploaded .glb places; none in use = the built-in temple.
export function useCharacterPlaces() {
  return useQuery({
    queryKey: ["character", "places"],
    queryFn: () => getJson<CharacterModelInfo[]>("/api/character/places"),
    retry: false,
  });
}
