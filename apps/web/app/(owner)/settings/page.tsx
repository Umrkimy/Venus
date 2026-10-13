"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

// Normally next.config.ts redirects /settings before this page is reached.
// The static demo has no server for that, so the page does it.
export default function SettingsIndex() {
  const router = useRouter();
  useEffect(() => router.replace("/settings/general"), [router]);
  return null;
}
