"use client";

import { useQuery } from "@tanstack/react-query";

import { getJson } from "@/lib/get-json";

type NodeList = { device_ids: string[] };

// The sidebar and the chat share this query key, so they share one fetch.
export function useNodes() {
  return useQuery({
    queryKey: ["nodes"],
    queryFn: () => getJson<NodeList>("/api/nodes"),
    refetchInterval: 5000,
  });
}
