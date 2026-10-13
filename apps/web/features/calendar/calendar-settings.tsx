"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, Copy } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import StatusBadge from "@/features/settings/status-badge";
import { getJson } from "@/lib/get-json";

type Provider = "google" | "microsoft";

type CalendarAccount = {
  provider: Provider;
  label: string;
  client_id: string | null;
  configured: boolean;
  connected: boolean;
  mail: boolean;
  email: string | null;
  redirect_uri: string;
};

const CONSOLE: Record<Provider, { name: string; url: string; where: string }> = {
  google: {
    name: "Google Cloud Console",
    url: "https://console.cloud.google.com/apis/credentials",
    where: "Credentials, OAuth client (Web application), Authorized redirect URIs",
  },
  microsoft: {
    name: "Microsoft Entra",
    url: "https://entra.microsoft.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade",
    where: "App registrations, Authentication, Web redirect URIs",
  },
};

function ProviderCard({ account, onChange }: { account: CalendarAccount; onChange: () => Promise<unknown> }) {
  const [clientId, setClientId] = useState(account.client_id ?? "");
  const [secret, setSecret] = useState("");
  const [setup, setSetup] = useState(!account.connected);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const console_ = CONSOLE[account.provider];

  async function send(url: string, init: RequestInit, failure: string) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(url, init);
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(typeof data?.detail === "string" ? data.detail : failure);
        return false;
      }
      await onChange();
      return true;
    } catch {
      setError("Can't reach Venus.");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const saved = await send(
      `/api/calendar/${account.provider}`,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId.trim(), client_secret: secret.trim() || null }),
      },
      "Couldn't save that.",
    );
    if (saved) setSecret("");
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(account.redirect_uri);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  }

  const status = account.connected ? (
    <StatusBadge tone="on">Connected</StatusBadge>
  ) : account.configured ? (
    <StatusBadge tone="warn">Not signed in</StatusBadge>
  ) : (
    <StatusBadge tone="off">Not set up</StatusBadge>
  );

  return (
    <section className="rounded-lg border border-border">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2 p-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold">{account.label}</h3>
            {status}
          </div>
          {account.connected && (
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
              {account.email && <span className="truncate">{account.email}</span>}
              <span className="flex items-center gap-1">
                <Check className="size-3 text-emerald-500" aria-hidden="true" /> Calendar
              </span>
              {account.mail && (
                <span className="flex items-center gap-1">
                  <Check className="size-3 text-emerald-500" aria-hidden="true" /> Mail
                </span>
              )}
            </p>
          )}
        </div>
        {account.configured && (
          <Button asChild size="sm" variant={account.connected ? "outline" : "default"} disabled={busy}>
            <a href={`/api/calendar/${account.provider}/connect`}>{account.connected ? "Reconnect" : "Sign in"}</a>
          </Button>
        )}
        {account.configured && (
          <Button
            size="sm"
            variant="ghost"
            disabled={busy}
            onClick={() => send(`/api/calendar/${account.provider}`, { method: "DELETE" }, "Couldn't remove it.")}
          >
            {account.connected ? "Disconnect" : "Remove"}
          </Button>
        )}
      </div>

      <div className="border-t border-border">
        <button
          type="button"
          onClick={() => setSetup(!setup)}
          aria-expanded={setup}
          className="flex w-full items-center gap-2 px-4 py-2.5 text-left text-xs font-medium text-muted-foreground hover:text-foreground"
        >
          App setup
          <ChevronDown className={`ml-auto size-4 transition-transform ${setup ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>
        {setup && (
          <form onSubmit={save} className="space-y-3 px-4 pb-4">
            <div>
              <p className="text-xs text-muted-foreground">
                1. In{" "}
                <a href={console_.url} target="_blank" rel="noreferrer" className="underline underline-offset-2 hover:text-foreground">
                  {console_.name}
                </a>{" "}
                ({console_.where}), add this exact address:
              </p>
              <div className="mt-1.5 flex items-center gap-2 rounded-md border border-border bg-muted/60 py-1 pr-1 pl-2.5">
                <code className="min-w-0 flex-1 truncate text-xs">{account.redirect_uri}</code>
                <Button type="button" variant="ghost" size="sm" onClick={copy} aria-label="Copy redirect address">
                  {copied ? <Check /> : <Copy />}
                  {copied ? "Copied" : "Copy"}
                </Button>
              </div>
            </div>
            <p className="text-xs text-muted-foreground">2. Paste the app&apos;s client ID and secret, then Save and Sign in.</p>
            <div className="grid gap-3 sm:grid-cols-2">
              <label className={LABEL_CLASS}>
                Client ID
                <Input value={clientId} onChange={(e) => setClientId(e.target.value)} autoComplete="off" className={FIELD_HOVER} />
              </label>
              <label className={LABEL_CLASS}>
                Client secret
                <Input
                  type="password"
                  value={secret}
                  onChange={(e) => setSecret(e.target.value)}
                  placeholder={account.configured ? "Saved" : ""}
                  autoComplete="off"
                  className={FIELD_HOVER}
                />
              </label>
            </div>
            <Button type="submit" size="sm" variant="outline" disabled={busy || !clientId.trim()}>
              Save
            </Button>
          </form>
        )}
      </div>
      {error && (
        <p role="alert" className="border-t border-border px-4 py-2.5 text-sm text-destructive">
          {error}
        </p>
      )}
    </section>
  );
}

export default function CalendarSettings() {
  const params = useSearchParams();
  const accounts = useQuery({
    queryKey: ["calendar"],
    queryFn: () => getJson<CalendarAccount[]>("/api/calendar"),
  });
  const justConnected = params.get("connected");
  const signInError = params.get("error");
  const label = accounts.data?.find((account) => account.provider === justConnected)?.label;

  return (
    <div className="space-y-3">
      {justConnected && (
        <p role="status" className="flex items-start gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm">
          <Check className="mt-0.5 size-4 shrink-0 text-emerald-500" aria-hidden="true" />
          <span>
            {label ?? "Calendar"} connected. Events show on the{" "}
            <Link href="/calendar" className="font-medium underline underline-offset-2">
              Calendar page
            </Link>
            .
          </span>
        </p>
      )}
      {signInError && (
        <p role="alert" className="rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {signInError}
        </p>
      )}
      {accounts.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load calendars.
        </p>
      )}
      {accounts.data?.map((account) => (
        <ProviderCard key={account.provider} account={account} onChange={() => accounts.refetch()} />
      ))}
    </div>
  );
}
