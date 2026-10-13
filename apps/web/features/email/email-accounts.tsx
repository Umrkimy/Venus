"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, Mail, Trash2 } from "lucide-react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import StatusBadge from "@/features/settings/status-badge";
import { getJson } from "@/lib/get-json";

export type EmailAccount = {
  id: string;
  address: string;
  display_name: string;
  kind: string;
  imap_host: string;
  smtp_host: string;
};

function message(data: { detail?: unknown }, fallback: string) {
  const first = Array.isArray(data.detail) ? data.detail[0]?.msg : data.detail;
  return typeof first === "string" ? first.replace(/^Value error, /, "") : fallback;
}

export function useEmailAccounts() {
  return useQuery({ queryKey: ["email-accounts"], queryFn: () => getJson<EmailAccount[]>("/api/email/accounts") });
}

// Settings, Email: the mailboxes Venus may read and send from.
export default function EmailAccounts() {
  const queryClient = useQueryClient();
  const accounts = useEmailAccounts();
  const params = useSearchParams();
  const signedIn = params.get("connected");
  const signInError = params.get("error");
  const [senderName, setSenderName] = useState("");
  const [address, setAddress] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [advanced, setAdvanced] = useState(false);
  const [imapHost, setImapHost] = useState("");
  const [imapPort, setImapPort] = useState("993");
  const [smtpHost, setSmtpHost] = useState("");
  const [smtpPort, setSmtpPort] = useState("465");
  const [smtpSecurity, setSmtpSecurity] = useState<"ssl" | "starttls">("ssl");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    const body = {
      address: address.trim(),
      display_name: name.trim(),
      password,
      ...(advanced && imapHost.trim()
        ? {
            imap_host: imapHost.trim(),
            imap_port: Number(imapPort),
            smtp_host: smtpHost.trim(),
            smtp_port: Number(smtpPort),
            smtp_security: smtpSecurity,
          }
        : {}),
    };
    try {
      const response = await fetch("/api/email/accounts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        const text = message(data, "Couldn't add that account.");
        setError(text);
        if (text.includes("servers")) setAdvanced(true);
        return;
      }
      setAddress("");
      setPassword("");
      setNotice(`Added ${data.address}. Open Email in the sidebar.`);
      await queryClient.invalidateQueries({ queryKey: ["email-accounts"] });
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  async function remove(account: EmailAccount) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(`/api/email/accounts/${account.id}`, { method: "DELETE" });
      if (!response.ok) setError(`Couldn't remove ${account.address}.`);
      await queryClient.invalidateQueries({ queryKey: ["email-accounts"] });
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      {accounts.isSuccess && accounts.data.length > 0 && (
        <ul className="mb-5 space-y-2">
          {accounts.data.map((account) => (
            <li
              key={account.id}
              className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 hover:border-foreground/30 hover:bg-muted/60"
            >
              <Mail className="size-4 shrink-0 text-muted-foreground" aria-hidden="true" />
              <div className="min-w-0 flex-1">
                <p className="flex items-center gap-2">
                  <span className="truncate text-sm font-medium">{account.address}</span>
                  <StatusBadge tone="on">Connected</StatusBadge>
                </p>
                <p className="truncate text-xs text-muted-foreground">
                  {account.display_name} ·{" "}
                  {account.kind === "imap"
                    ? "App password"
                    : account.kind === "google"
                      ? "Google sign-in"
                      : "Microsoft sign-in"}
                </p>
              </div>
              <Button
                type="button"
                variant="ghost"
                size="icon-sm"
                disabled={busy}
                onClick={() => remove(account)}
                aria-label={`Remove ${account.address}`}
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
      )}

      {signedIn && (
        <p
          role="status"
          className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm"
        >
          <Check className="size-4 text-emerald-500" aria-hidden="true" />
          Mailbox connected.
          <Link href="/email" className="font-medium underline underline-offset-2">
            Open Email
          </Link>
        </p>
      )}
      {signInError && (
        <p
          role="alert"
          className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive"
        >
          {signInError}
        </p>
      )}
      {accounts.isSuccess && accounts.data.length === 0 && (
        <p className="mb-4">
          <StatusBadge tone="off">No mailbox yet</StatusBadge>
        </p>
      )}

      <Tabs defaultValue="sign-in">
        <TabsList>
          <TabsTrigger value="sign-in">Microsoft or Google sign-in</TabsTrigger>
          <TabsTrigger value="password">App password</TabsTrigger>
        </TabsList>
        <TabsContent value="sign-in" className="mt-3 space-y-3">
          <p className="text-sm text-muted-foreground">
            Uni Microsoft 365, Outlook.com, Gmail. Uses the app from Settings, Calendar.
          </p>
          <label className={LABEL_CLASS}>
            Your name (on mail you send)
            <Input
              value={senderName}
              onChange={(e) => setSenderName(e.target.value)}
              maxLength={100}
              placeholder="Umar Hakimi"
              className={FIELD_HOVER}
            />
          </label>
          <div className="flex flex-wrap gap-2">
            {(["microsoft", "google"] as const).map((provider) => (
              <Button key={provider} variant="outline" asChild>
                <a href={`/api/calendar/${provider}/connect?mail=true&name=${encodeURIComponent(senderName.trim())}`}>
                  {provider === "microsoft" ? "Sign in with Microsoft" : "Sign in with Google"}
                </a>
              </Button>
            ))}
          </div>
        </TabsContent>

        <TabsContent value="password" className="mt-3">
          <form onSubmit={add} className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Gmail, iCloud, Yahoo and others. Make an app password in your account&apos;s security settings.
            </p>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className={LABEL_CLASS}>
                Email address
                <Input
                  type="email"
                  value={address}
                  onChange={(e) => setAddress(e.target.value)}
                  placeholder="you@gmail.com"
                  autoComplete="off"
                  className={FIELD_HOVER}
                />
              </label>
              <label className={LABEL_CLASS}>
                Your name (on mail you send)
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={100}
                  placeholder="Umar Hakimi"
                  className={FIELD_HOVER}
                />
              </label>
            </div>
            <label className={LABEL_CLASS}>
              App password
              <Input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
                className={FIELD_HOVER}
              />
              <span className="mt-1 block text-xs font-normal text-muted-foreground">
                Checked before saving, stored encrypted.
              </span>
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="size-4 accent-primary"
                checked={advanced}
                onChange={(e) => setAdvanced(e.target.checked)}
              />
              Set the mail servers myself
            </label>
            {advanced && (
              <div className="grid gap-4 sm:grid-cols-2">
                <label className={LABEL_CLASS}>
                  IMAP server (reading)
                  <Input
                    value={imapHost}
                    onChange={(e) => setImapHost(e.target.value)}
                    placeholder="imap.example.com"
                    className={FIELD_HOVER}
                  />
                </label>
                <label className={LABEL_CLASS}>
                  IMAP port
                  <Input
                    value={imapPort}
                    onChange={(e) => setImapPort(e.target.value)}
                    inputMode="numeric"
                    className={FIELD_HOVER}
                  />
                </label>
                <label className={LABEL_CLASS}>
                  SMTP server (sending)
                  <Input
                    value={smtpHost}
                    onChange={(e) => setSmtpHost(e.target.value)}
                    placeholder="smtp.example.com"
                    className={FIELD_HOVER}
                  />
                </label>
                <label className={LABEL_CLASS}>
                  SMTP port
                  <Input
                    value={smtpPort}
                    onChange={(e) => {
                      setSmtpPort(e.target.value);
                      setSmtpSecurity(e.target.value.trim() === "587" ? "starttls" : "ssl");
                    }}
                    inputMode="numeric"
                    className={FIELD_HOVER}
                  />
                  <span className="mt-1 block text-xs font-normal text-muted-foreground">
                    465 = SSL, 587 = STARTTLS.
                  </span>
                </label>
              </div>
            )}
            <div className="flex items-center gap-3">
              <Button type="submit" disabled={busy || !address.trim() || !name.trim() || !password}>
                {busy ? "Checking..." : "Add account"}
              </Button>
              <p aria-live="polite" className="text-sm">
                {error && <span className="text-destructive">{error}</span>}
                {notice && <span className="text-muted-foreground">{notice}</span>}
              </p>
            </div>
          </form>
        </TabsContent>
      </Tabs>
    </div>
  );
}
