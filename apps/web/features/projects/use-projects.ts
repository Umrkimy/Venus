"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type Project = {
  id: string;
  name: string;
  updated_at: string;
  archived: boolean;
  // Archived chats count too: deleting the project deletes them all.
  chat_count: number;
  // Extra rules Venus follows in this project's chats; null when there are none.
  instructions: string | null;
};

export function useProjects() {
  return useQuery({
    queryKey: ["projects"],
    queryFn: () => getJson<Project[]>("/api/projects"),
  });
}

// Its key starts with "projects", so every refresh of the list above refreshes this too.
export function useArchivedProjects() {
  return useQuery({
    queryKey: ["projects", "archived"],
    queryFn: () => getJson<Project[]>("/api/projects?archived=true"),
  });
}

// Create, rename, archive, instructions and delete. Each returns null or false when it failed,
// and `error` says why.
export function useProjectActions() {
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);

  async function send(url: string, init: RequestInit, failure: string) {
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        setError(failure);
        return null;
      }
      await queryClient.invalidateQueries({ queryKey: ["projects"] });
      return response;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return null;
    }
  }

  function nameRequest(method: string, name: string): RequestInit {
    return {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    };
  }

  async function create(name: string): Promise<Project | null> {
    const response = await send(
      "/api/projects",
      nameRequest("POST", name),
      "Couldn't create that project.",
    );
    return response ? response.json() : null;
  }

  async function rename(id: string, name: string) {
    const response = await send(
      `/api/projects/${id}`,
      nameRequest("PATCH", name),
      "Couldn't rename that project.",
    );
    return response !== null;
  }

  async function setArchived(id: string, archived: boolean) {
    const response = await send(
      `/api/projects/${id}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ archived }),
      },
      archived ? "Couldn't archive that project." : "Couldn't unarchive that project.",
    );
    return response !== null;
  }

  async function setInstructions(id: string, instructions: string) {
    const response = await send(
      `/api/projects/${id}`,
      {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instructions }),
      },
      "Couldn't save the instructions.",
    );
    return response !== null;
  }

  async function remove(id: string) {
    const response = await send(
      `/api/projects/${id}`,
      { method: "DELETE" },
      "Couldn't delete that project.",
    );
    // Its chats were deleted with it, so the chat lists changed too.
    if (response) {
      await queryClient.invalidateQueries({ queryKey: ["conversations"] });
    }
    return response !== null;
  }

  return { error, create, rename, setArchived, setInstructions, remove };
}
