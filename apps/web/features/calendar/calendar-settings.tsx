"use client";

import { useQuery } from "@tanstack/react-query";
import { CalendarCheck, Copy } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import { getJson } from "@/lib/get-json";

type Provider = "google" | "microsoft";

type CalendarAccount = {
  provider: Provider;
  label: string;
  client_id: string | null;
  configured: boolean;
  connected: boolean;
  email: string | null;
  redirect_uri: string;
};

type CalendarEvent = {
  id: string;
  title: string;
  start: string;
  all_day: boolean;
  source: string;
  location: string;
};

const WHERE: Record<Provider, string> = {
  google: "Google Cloud Console: APIs & Services, Credentials, OAuth client (Web application)",
  microsoft: "Microsoft Entra admin center: App registrations (Web platform)",
};

function when(event: CalendarEvent) {
  const start = new Date(event.start);
  const day = start.toLocaleDateString(undefined, { weekday: "short", day: "numeric", month: "short" });
  if (event.all_day) return `${day}, all day`;
  return `${day}, ${start.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`;
}

function ProviderCard({ account, onChange }: { account: CalendarAccount; onChange: () => Promise<unknown> }) {
  const [clientId, setClientId] = useState(account.client_id ?? "");
  const [secret, setSecret] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

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
      setError("Can't reach Venus. Is it running?");
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
    } catch {
      setCopied(false);
    }
  }

  return (
    <section className="rounded-lg border border-border px-4 py-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold">{account.label}</h3>
        <span className={`text-xs ${account.connected ? "text-foreground" : "text-muted-foreground"}`}>
          {account.connected ? `Connected${account.email ? ` as ${account.email}` : ""}` : "Not connected"}
        </span>
      </div>

      <form onSubmit={save} className="mt-3 space-y-3">
        <p className="text-xs text-muted-foreground">
          Make your own app in {WHERE[account.provider]} and add this redirect address:
        </p>
        <div className="flex items-center gap-2">
          <code className="min-w-0 flex-1 truncate rounded bg-muted px-2 py-1 text-xs">{account.redirect_uri}</code>
          <Button type="button" variant="ghost" size="icon-sm" onClick={copy} aria-label="Copy redirect address">
            <Copy />
          </Button>
          <span aria-live="polite" className="text-xs text-muted-foreground">
            {copied ? "Copied" : ""}
          </span>
        </div>
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
            placeholder={account.configured ? "Saved (type to replace)" : ""}
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <div className="flex flex-wrap items-center gap-2">
          <Button type="submit" variant="outline" disabled={busy || !clientId.trim()}>
            Save
          </Button>
          {account.configured && (
            // A real page change: Google or Microsoft asks you, then sends you back here.
            <Button asChild disabled={busy}>
              <a href={`/api/calendar/${account.provider}/connect`}>
                {account.connected ? "Reconnect" : `Connect ${account.label}`}
              </a>
            </Button>
          )}
          {account.configured && (
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={() =>
                send(`/api/calendar/${account.provider}`, { method: "DELETE" }, "Couldn't disconnect.")
              }
            >
              Remove
            </Button>
          )}
        </div>
        {error && (
          <p role="alert" className="text-sm text-destructive">
            {error}
          </p>
        )}
      </form>
    </section>
  );
}

// Settings, Calendar: connect Google and Outlook, see what Venus sees.
export default function CalendarSettings() {
  const params = useSearchParams();
  const accounts = useQuery({
    queryKey: ["calendar"],
    queryFn: () => getJson<CalendarAccount[]>("/api/calendar"),
  });
  const connected = accounts.data?.some((account) => account.connected) ?? false;
  const events = useQuery({
    queryKey: ["calendar", "events"],
    queryFn: () => getJson<{ events: CalendarEvent[]; errors: string[] }>("/api/calendar/events"),
    enabled: connected,
  });
  const justConnected = params.get("connected");
  const signInError = params.get("error");

  return (
    <div className="space-y-4">
      {justConnected && (
        <p role="status" className="text-sm">
          Connected. Venus can see your calendar now.
        </p>
      )}
      {signInError && (
        <p role="alert" className="text-sm text-destructive">
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

      {connected && (
        <section>
          <h3 className="flex items-center gap-2 text-sm font-semibold">
            <CalendarCheck className="size-4" aria-hidden="true" /> What Venus sees (next 7 days)
          </h3>
          {events.data?.errors.map((problem) => (
            <p key={problem} role="alert" className="mt-2 text-sm text-destructive">
              {problem}
            </p>
          ))}
          {events.data && events.data.events.length === 0 && (
            <p className="mt-2 text-sm text-muted-foreground">Nothing in the next 7 days.</p>
          )}
          <ul className="mt-2 space-y-1">
            {events.data?.events.slice(0, 15).map((event) => (
              <li key={event.id} className="flex gap-3 text-sm">
                <span className="w-36 shrink-0 text-muted-foreground">{when(event)}</span>
                <span className="min-w-0 truncate">
                  {event.title}
                  {event.location && <span className="text-muted-foreground"> · {event.location}</span>}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
