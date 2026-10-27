"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import StatusBadge from "@/features/settings/status-badge";
import { errorText } from "@/lib/error-text";
import { getJson } from "@/lib/get-json";

type Assistant = { url: string | null; connected: boolean };

type Entity = {
  entity_id: string;
  kind: "light" | "plug" | "tv" | "aircon" | "scene";
  friendly_name: string;
  name: string;
  added_as: string | null;
};

const KIND_LABELS: Record<Entity["kind"], string> = {
  light: "Light",
  plug: "Switch",
  tv: "TV / speaker",
  aircon: "Air-con",
  scene: "Scene",
};

const EXAMPLES: Record<Entity["kind"], (name: string) => string> = {
  light: (name) => `turn off the ${name}`,
  plug: (name) => `turn on the ${name}`,
  tv: (name) => `turn on the ${name}`,
  aircon: (name) => `set the ${name} to 24`,
  scene: (name) => name,
};

// Settings, Home: connect Home Assistant, then tick which of its devices Venus may control.
export default function HomeAssistant() {
  const queryClient = useQueryClient();
  const [url, setUrl] = useState("");
  const [token, setToken] = useState("");
  const [editing, setEditing] = useState(false);
  const [picked, setPicked] = useState<Map<string, string>>(new Map());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const assistant = useQuery({
    queryKey: ["home-assistant"],
    queryFn: () => getJson<Assistant>("/api/home/assistant"),
  });
  const entities = useQuery({
    queryKey: ["home-assistant-entities"],
    queryFn: async () => {
      const response = await fetch("/api/home/assistant/entities");
      const data = await response.json();
      if (!response.ok) throw new Error(errorText(data, "Couldn't get the devices."));
      return data as Entity[];
    },
    enabled: false,
    retry: false,
  });
  const connected = assistant.data?.connected ?? false;

  async function send(path: string, method: string, body?: unknown) {
    const response = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = response.status === 204 ? {} : await response.json();
    return { ok: response.ok, data };
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const { ok, data } = await send("/api/home/assistant", "PUT", {
        url: url.trim(),
        token: token.trim() || null,
      });
      if (!ok) {
        setError(errorText(data, "Check the address and token."));
        return;
      }
      setToken("");
      setEditing(false);
      await assistant.refetch();
      const found = await entities.refetch();
      if (found.isError) setError(found.error.message);
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      await send("/api/home/assistant", "DELETE");
      setPicked(new Map());
      queryClient.removeQueries({ queryKey: ["home-assistant-entities"] });
      await Promise.all([assistant.refetch(), queryClient.invalidateQueries({ queryKey: ["home-devices"] })]);
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  function toggle(entity: Entity, on: boolean) {
    const next = new Map(picked);
    if (on) next.set(entity.entity_id, entity.name);
    else next.delete(entity.entity_id);
    setPicked(next);
  }

  function rename(entityId: string, name: string) {
    setPicked(new Map(picked).set(entityId, name));
  }

  async function addPicked() {
    setBusy(true);
    setError(null);
    setNotice(null);
    const added: string[] = [];
    const failed: string[] = [];
    try {
      for (const entity of entities.data ?? []) {
        const name = picked.get(entity.entity_id);
        if (name === undefined) continue;
        const { ok, data } = await send("/api/home/devices", "POST", {
          name: name.trim(),
          kind: entity.kind,
          ha_entity_id: entity.entity_id,
        });
        if (ok) added.push(EXAMPLES[entity.kind](data.name));
        else failed.push(`${name || entity.friendly_name}: ${errorText(data, "not added")}`);
      }
      setPicked(new Map());
      if (added.length) setNotice(`Added. Try: ${added.slice(0, 3).join(", ")}`);
      if (failed.length) setError(failed.join(". "));
      await Promise.all([entities.refetch(), queryClient.invalidateQueries({ queryKey: ["home-devices"] })]);
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  const status = (
    <p aria-live="polite" className="text-sm">
      {error && <span className="text-destructive">{error}</span>}
      {notice && <span className="text-muted-foreground">{notice}</span>}
    </p>
  );

  if (assistant.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading Home Assistant</span>
        <div className="h-12 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (!connected || editing) {
    return (
      <form onSubmit={save} className="space-y-4">
        <StatusBadge tone="off">Not connected</StatusBadge>
        <label className={LABEL_CLASS}>
          Address
          <Input
            value={url}
            onChange={(event) => setUrl(event.target.value)}
            placeholder={assistant.data?.url ?? "http://192.168.1.50:8123"}
            autoComplete="off"
            className={FIELD_HOVER}
          />
          <span className="mt-1 block text-xs font-normal text-muted-foreground">
            Use the IP address if homeassistant.local doesn&apos;t work.
          </span>
        </label>
        <label className={LABEL_CLASS}>
          Long-lived access token
          <Input
            type="password"
            value={token}
            onChange={(event) => setToken(event.target.value)}
            placeholder={connected ? "Leave empty to keep the saved one" : ""}
            autoComplete="off"
            className={FIELD_HOVER}
          />
          <span className="mt-1 block text-xs font-normal text-muted-foreground">
            Home Assistant: Profile, Security, Long-lived access tokens.
          </span>
        </label>
        <div className="flex items-center gap-3">
          <Button type="submit" disabled={busy || !url.trim() || (!connected && !token.trim())}>
            {connected ? "Save" : "Connect"}
          </Button>
          {editing && (
            <Button type="button" variant="ghost" onClick={() => setEditing(false)} disabled={busy}>
              Cancel
            </Button>
          )}
          {status}
        </div>
      </form>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <StatusBadge tone="on">Connected</StatusBadge>
        <p className="min-w-0 flex-1 truncate text-sm text-muted-foreground">{assistant.data?.url}</p>
        <Button
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            setUrl(assistant.data?.url ?? "");
            setEditing(true);
          }}
          disabled={busy}
        >
          Change
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={disconnect} disabled={busy}>
          Disconnect
        </Button>
      </div>
      <Button type="button" variant="outline" onClick={() => entities.refetch()} disabled={busy || entities.isFetching}>
        {entities.isFetching ? "Looking..." : entities.data ? "Look again" : "Find devices"}
      </Button>
      {entities.isError && (
        <p role="alert" className="text-sm text-destructive">
          {entities.error.message}
        </p>
      )}
      {entities.data && entities.data.length === 0 && (
        <p className="text-sm text-muted-foreground">No supported devices found.</p>
      )}
      {entities.data && entities.data.length > 0 && (
        <>
          <ul className="space-y-2">
            {entities.data.map((entity) => {
              const name = picked.get(entity.entity_id);
              const checkboxId = `ha-${entity.entity_id}`;
              return (
                <li
                  key={entity.entity_id}
                  className="flex flex-wrap items-center gap-3 rounded-lg border border-border px-4 py-2 hover:border-foreground/30"
                >
                  <input
                    id={checkboxId}
                    type="checkbox"
                    className="size-4 accent-primary"
                    checked={name !== undefined}
                    disabled={busy || entity.added_as !== null}
                    onChange={(event) => toggle(entity, event.target.checked)}
                  />
                  <label htmlFor={checkboxId} className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium">{entity.friendly_name}</span>
                    <span className="block truncate text-xs text-muted-foreground">
                      {KIND_LABELS[entity.kind]}
                      {entity.added_as !== null && ` · added as "${entity.added_as}"`}
                    </span>
                  </label>
                  {name !== undefined && (
                    <Input
                      aria-label={`Name for ${entity.friendly_name} (what you say)`}
                      value={name}
                      onChange={(event) => rename(entity.entity_id, event.target.value)}
                      maxLength={40}
                      autoComplete="off"
                      className={`h-8 w-full sm:w-48 ${FIELD_HOVER}`}
                    />
                  )}
                </li>
              );
            })}
          </ul>
          <div className="flex items-center gap-3">
            <Button type="button" onClick={addPicked} disabled={busy || picked.size === 0}>
              Add {picked.size > 0 ? picked.size : ""} selected
            </Button>
            {status}
          </div>
        </>
      )}
      {!entities.data && status}
    </div>
  );
}
