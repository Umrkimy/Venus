"use client";

import Link from "next/link";
import NodeCommands from "@/features/nodes/node-commands";
import OwnerStatus from "@/features/owner/owner-status";
import { useOwner } from "@/lib/use-owner";

export default function Home() {
  const { owner, logout } = useOwner();

  return (
    <main className="mx-auto w-full max-w-sm px-4 pt-24">
      <h1 className="text-2xl font-semibold tracking-tight">Venus</h1>

      <OwnerStatus owner={owner} />

      {owner.status === "signed-in" && (
        <>
          <div className="mt-4 flex items-center justify-between gap-4">
            <p className="text-muted">
              Signed in as{" "}
              <span className="font-medium text-foreground">
                {owner.username}
              </span>
            </p>
            <Link
              href="/settings"
              className="rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent"
            >
              Settings
            </Link>
          </div>
          <NodeCommands />
          <button
            type="button"
            onClick={logout}
            className="mt-8 rounded-md border border-border px-4 py-2 font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent motion-safe:transition-transform motion-safe:active:scale-[0.98]"
          >
            Log out
          </button>
        </>
      )}
    </main>
  );
}
