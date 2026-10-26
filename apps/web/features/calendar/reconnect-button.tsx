"use client";

import { RefreshCw, X } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type SignInProvider = "google" | "microsoft";
type Back = "email" | "calendar" | "home";

const LABELS: Record<SignInProvider, string> = { google: "Google", microsoft: "Microsoft" };

export function isSignInProvider(kind: string | undefined): kind is SignInProvider {
  return kind === "google" || kind === "microsoft";
}

// Signs in again right here and comes back to this page; no trip to Settings.
export default function ReconnectButton({
  provider,
  back,
  size = "sm",
  className,
}: {
  provider: SignInProvider;
  back: Back;
  size?: "sm" | "xs";
  className?: string;
}) {
  return (
    <Button asChild size={size} className={className}>
      <a href={`/api/calendar/${provider}/connect?back=${back}`}>
        <RefreshCw />
        Reconnect {LABELS[provider]}
      </a>
    </Button>
  );
}

function Notice() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const connected = params.get("connected");
  const error = params.get("error");
  if (!connected && !error) return null;
  const label = isSignInProvider(connected ?? undefined) ? LABELS[connected as SignInProvider] : "Your account";

  return (
    <p
      role={error ? "alert" : "status"}
      className={cn(
        "flex items-start gap-2 rounded-lg border px-3 py-2 text-sm",
        error ? "border-destructive/30 bg-destructive/10 text-destructive" : "border-emerald-500/30 bg-emerald-500/10",
      )}
    >
      <span className="min-w-0 flex-1">{error ?? `${label} is connected again.`}</span>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={() => router.replace(pathname)}
        className="cursor-pointer rounded-sm opacity-70 hover:opacity-100"
      >
        <X className="size-4" />
      </button>
    </p>
  );
}

// "Connected again" or what went wrong, after coming back from signing in.
export function SignInNotice() {
  return (
    <Suspense>
      <Notice />
    </Suspense>
  );
}
