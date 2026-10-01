"use client";

import Link from "next/link";
import OwnerStatus from "@/features/owner/owner-status";
import ModeSwitch from "@/features/settings/mode-switch";
import Shortcuts from "@/features/shortcuts/shortcuts";
import { useOwner } from "@/lib/use-owner";

export default function SettingsPage() {
  const { owner } = useOwner();

  return (
    <main className="mx-auto w-full max-w-sm px-4 pt-24">
      <Link
        href="/"
        className="text-sm text-muted outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-accent"
      >
        &larr; Back
      </Link>
      <h1 className="mt-2 text-2xl font-semibold tracking-tight">Settings</h1>

      <OwnerStatus owner={owner} />

      {owner.status === "signed-in" && (
        <>
          <ModeSwitch />
          <Shortcuts />
        </>
      )}
    </main>
  );
}
