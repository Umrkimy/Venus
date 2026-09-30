"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import AppPicker, { type NodeApp } from "./app-picker";
import UrlOpener from "./url-opener";
import { getJson } from "./get-json";

type NodeList = { device_ids: string[] };
type CommandStatus = { command_id: string; status: string; detail?: string };

// Once a command reaches one of these, it never changes again.
const FINAL_STATUSES = ["succeeded", "failed", "denied", "expired", "unknown"];

const STATUS_TEXT: Record<string, string> = {
  dispatched: "Sent to your PC…",
  succeeded: "Opened.",
  failed: "Your PC couldn't open it.",
  denied: "Denied.",
  expired: "Expired before you decided.",
  unknown: "No answer from your PC.",
};

export default function NodeCommands() {
  const [commandId, setCommandId] = useState<string | null>(null);
  const [targetName, setTargetName] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const nodes = useQuery({
    queryKey: ["nodes"],
    queryFn: () => getJson<NodeList>("/api/nodes"),
    refetchInterval: 5000,
  });

  const command = useQuery({
    queryKey: ["command", commandId],
    queryFn: () => getJson<CommandStatus>(`/api/commands/${commandId}`),
    enabled: commandId !== null,
    refetchInterval: (query) =>
      FINAL_STATUSES.includes(query.state.data?.status ?? "") ? false : 1000,
  });

  const status = command.data?.status;
  const inFlight = commandId !== null && !FINAL_STATUSES.includes(status ?? "");

  async function post(url: string, body?: object) {
    setBusy(true);
    setError(null);
    try {
      const response = await fetch(url, {
        method: "POST",
        headers: body ? { "Content-Type": "application/json" } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      const data = await response.json();
      if (!response.ok) {
        setError(
          typeof data.detail === "string"
            ? data.detail
            : "Something went wrong.",
        );
        return null;
      }
      return data;
    } catch {
      setError("Can't reach Venus Core. Is it running?");
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function propose(deviceId: string, app: NodeApp) {
    const data = await post(
      `/api/nodes/${encodeURIComponent(deviceId)}/commands`,
      { application_id: app.app_id },
    );
    if (data) {
      setTargetName(app.name);
      setCommandId(data.command_id);
    }
  }

  async function proposeUrl(deviceId: string, url: string) {
    const data = await post(
      `/api/nodes/${encodeURIComponent(deviceId)}/commands/open-url`,
      { url },
    );
    if (data) {
      setTargetName(data.url);
      setCommandId(data.command_id);
    }
  }

  async function decide(approved: boolean) {
    if (commandId === null) return;
    await post(`/api/commands/${commandId}/approval`, { approved });
    await command.refetch();
  }

  return (
    <section className="mt-10">
      <h2 className="text-sm font-medium text-muted">Your devices</h2>

      {nodes.isPending && (
        <div role="status" className="mt-2">
          <span className="sr-only">Loading devices</span>
          <div className="h-12 w-full rounded-md bg-muted/20 motion-safe:animate-pulse" />
        </div>
      )}

      {nodes.isError && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Can&apos;t load devices.
        </p>
      )}

      {nodes.data && nodes.data.device_ids.length === 0 && (
        <p className="mt-2 text-sm text-muted">
          No devices online. Start Venus Node on your PC.
        </p>
      )}

      <ul className="mt-2 space-y-2">
        {nodes.data?.device_ids.map((deviceId) => (
          <li
            key={deviceId}
            className="rounded-md border border-border px-4 py-3"
          >
            <span className="font-medium">{deviceId}</span>
            <AppPicker
              deviceId={deviceId}
              disabled={busy || inFlight}
              onOpen={(app) => propose(deviceId, app)}
            />
            <UrlOpener
              deviceId={deviceId}
              disabled={busy || inFlight}
              onOpen={(url) => proposeUrl(deviceId, url)}
            />
          </li>
        ))}
      </ul>

      {status === "awaiting_approval" && (
        <div className="mt-6 rounded-md border border-border p-4">
          <p className="break-all">Open {targetName} on this PC?</p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => decide(true)}
              disabled={busy}
              className="rounded-md bg-accent px-4 py-2 font-medium text-accent-foreground outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
            >
              Approve
            </button>
            <button
              type="button"
              onClick={() => decide(false)}
              disabled={busy}
              className="rounded-md border border-border px-4 py-2 font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
            >
              Deny
            </button>
          </div>
        </div>
      )}

      {status && status !== "awaiting_approval" && (
        <p role="status" className="mt-6 text-sm">
          {STATUS_TEXT[status] ?? status}
        </p>
      )}

      {command.isError && (
        <p role="alert" className="mt-4 text-sm text-danger">
          Lost track of this command.
        </p>
      )}

      {error && (
        <p role="alert" className="mt-4 text-sm text-danger">
          {error}
        </p>
      )}
    </section>
  );
}
