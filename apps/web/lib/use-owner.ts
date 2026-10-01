"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

export type OwnerState =
  | { status: "loading" }
  | { status: "signed-in"; username: string }
  | { status: "unreachable" };

// Shared by every owner page: who is signed in, or off to /login.
export function useOwner() {
  const router = useRouter();
  const [owner, setOwner] = useState<OwnerState>({ status: "loading" });

  useEffect(() => {
    let cancelled = false;

    async function loadOwner() {
      try {
        const response = await fetch("/api/auth/me");
        if (cancelled) return;
        if (response.status === 401) {
          router.replace("/login");
          return;
        }
        if (!response.ok) {
          setOwner({ status: "unreachable" });
          return;
        }
        const body: { username: string } = await response.json();
        if (!cancelled) {
          setOwner({ status: "signed-in", username: body.username });
        }
      } catch {
        if (!cancelled) setOwner({ status: "unreachable" });
      }
    }

    loadOwner();
    return () => {
      cancelled = true;
    };
  }, [router]);

  async function logout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
    } catch {
      setOwner({ status: "unreachable" });
    }
  }

  return { owner, logout };
}
