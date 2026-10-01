"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import NodeCommands from "@/features/nodes/node-commands";
import ModeSwitch from "@/features/settings/mode-switch";
import Shortcuts from "@/features/shortcuts/shortcuts";

type OwnerState =
  | { status: "loading" }
  | { status: "signed-in"; username: string }
  | { status: "unreachable" };

export default function Home() {
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

  async function handleLogout() {
    try {
      await fetch("/api/auth/logout", { method: "POST" });
      router.replace("/login");
    } catch {
      setOwner({ status: "unreachable" });
    }
  }

  return (
    <main className="mx-auto w-full max-w-sm px-4 pt-24">
      <h1 className="text-2xl font-semibold tracking-tight">Venus</h1>

      {owner.status === "loading" && (
        <div role="status" className="mt-4">
          <span className="sr-only">Loading</span>
          <div className="h-5 w-40 rounded-md bg-muted/20 motion-safe:animate-pulse" />
        </div>
      )}

      {owner.status === "unreachable" && (
        <p role="alert" className="mt-4 text-sm text-danger">
          Can&apos;t reach Venus Core. Is it running?
        </p>
      )}

      {owner.status === "signed-in" && (
        <>
          <p className="mt-4 text-muted">
            Signed in as{" "}
            <span className="font-medium text-foreground">
              {owner.username}
            </span>
          </p>
          <ModeSwitch />
          <NodeCommands />
          <Shortcuts />
          <button
            type="button"
            onClick={handleLogout}
            className="mt-8 rounded-md border border-border px-4 py-2 font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent motion-safe:transition-transform motion-safe:active:scale-[0.98]"
          >
            Log out
          </button>
        </>
      )}
    </main>
  );
}
