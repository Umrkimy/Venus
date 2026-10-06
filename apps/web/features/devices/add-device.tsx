"use client";

import { Check, Copy } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import { NAME_LIMIT } from "./use-devices";

type AddDeviceProps = {
  // Resolves to the new token, or null when it failed.
  onAdd: (name: string) => Promise<string | null>;
};

// Name a new PC, then show its token once to paste into that PC's apps/node/.env.
export default function AddDevice({ onAdd }: AddDeviceProps) {
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const newToken = await onAdd(name.trim());
    setBusy(false);
    if (newToken) {
      setToken(newToken);
      setCopied(false);
      setName("");
    }
  }

  async function copy() {
    if (!token) return;
    try {
      await navigator.clipboard.writeText(`VENUS_NODE_CORE_DEV_TOKEN=${token}`);
      setCopied(true);
    } catch {
      // The clipboard needs https or localhost; the line can still be selected by hand.
    }
  }

  return (
    <div className="space-y-3">
      <form onSubmit={submit} className="flex gap-2">
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={NAME_LIMIT}
          aria-label="Device name"
          placeholder="e.g. Laptop"
          className="hover:border-foreground/40"
        />
        <Button
          type="submit"
          variant="outline"
          disabled={busy || name.trim() === ""}
        >
          {busy ? "Adding…" : "Add device"}
        </Button>
      </form>
      {token && (
        <div className="space-y-2 rounded-lg border border-border bg-muted/40 p-3">
          <p className="text-sm">
            Put this line in <code>apps/node/.env</code> on that PC, then
            restart Venus there. It is shown only once.
          </p>
          <div className="flex items-start gap-2">
            <code className="min-w-0 flex-1 rounded bg-background p-2 text-xs break-all select-all">
              VENUS_NODE_CORE_DEV_TOKEN={token}
            </code>
            <Button
              variant="ghost"
              size="icon-sm"
              aria-label={copied ? "Copied" : "Copy token line"}
              onClick={copy}
            >
              {copied ? <Check /> : <Copy />}
            </Button>
          </div>
          <Button variant="ghost" size="sm" onClick={() => setToken(null)}>
            Done
          </Button>
        </div>
      )}
    </div>
  );
}
