"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
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
                <p className="truncate text-sm font-medium">{account.address}</p>
                <p className="truncate text-xs text-muted-foreground">
                  Sends as {account.display_name} · {account.imap_host}
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

      <form onSubmit={add} className="space-y-4">
        <p className="text-sm font-semibold">Add an account</p>
        <p className="text-sm text-muted-foreground">
          Venus signs in with an <b>app password</b>, a separate password just for Venus, never your normal one.
          Gmail: Google Account, Security, 2-Step Verification on, then App passwords. iCloud and Yahoo have the same
          in their account security settings. Uni Microsoft 365 and Outlook.com need the Microsoft sign-in (coming next).
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
            <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={100} placeholder="Umar Hakimi" className={FIELD_HOVER} />
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
            Venus checks it signs in before saving. Saved encrypted and never shown again.
          </span>
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" className="size-4 accent-primary" checked={advanced} onChange={(e) => setAdvanced(e.target.checked)} />
          Set the mail servers myself (only for providers Venus doesn&apos;t know)
        </label>
        {advanced && (
          <div className="grid gap-4 sm:grid-cols-2">
            <label className={LABEL_CLASS}>
              IMAP server (reading)
              <Input value={imapHost} onChange={(e) => setImapHost(e.target.value)} placeholder="imap.example.com" className={FIELD_HOVER} />
            </label>
            <label className={LABEL_CLASS}>
              IMAP port
              <Input value={imapPort} onChange={(e) => setImapPort(e.target.value)} inputMode="numeric" className={FIELD_HOVER} />
            </label>
            <label className={LABEL_CLASS}>
              SMTP server (sending)
              <Input value={smtpHost} onChange={(e) => setSmtpHost(e.target.value)} placeholder="smtp.example.com" className={FIELD_HOVER} />
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
              <span className="mt-1 block text-xs font-normal text-muted-foreground">465 = SSL, 587 = STARTTLS.</span>
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
    </div>
  );
}
