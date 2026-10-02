"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getJson } from "@/lib/get-json";

import { FIELD_HOVER, LABEL_CLASS, SELECT_CLASS } from "./field-styles";

type Provider = "fake" | "openai";
type LlmResponse = { provider: Provider; model: string; has_key: boolean };

const PROVIDERS: Provider[] = ["fake", "openai"];

export default function LlmSettings() {
  const llm = useQuery({
    queryKey: ["llm"],
    queryFn: () => getJson<LlmResponse>("/api/settings/llm"),
  });

  if (llm.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading LLM settings</span>
        <div className="h-8 w-36 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (llm.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the LLM settings.
      </p>
    );
  }

  return <LlmForm initial={llm.data} />;
}

function LlmForm({ initial }: { initial: LlmResponse }) {
  const [provider, setProvider] = useState<Provider>(initial.provider);
  const [model, setModel] = useState(initial.model);
  const [apiKey, setApiKey] = useState("");
  const [hasKey, setHasKey] = useState(initial.has_key);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);

    // Leave api_key out when the box is empty so Core keeps the saved key.
    const body: { provider: Provider; model: string; api_key?: string } = {
      provider,
      model: model.trim(),
    };
    if (apiKey) body.api_key = apiKey;

    try {
      const response = await fetch("/api/settings/llm", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (response.status === 409) {
        // Core has no secret key to encrypt with; show its own instructions.
        const data = await response.json();
        setError(data.detail);
        return;
      }
      if (!response.ok) {
        setError("Saving settings failed.");
        return;
      }
      const saved: LlmResponse = await response.json();
      setHasKey(saved.has_key);
      setMessage(
        `Saved: ${saved.provider}, ${saved.model}${apiKey ? ", key updated" : ""}`,
      );
      setApiKey("");
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={LABEL_CLASS}>
          Provider
          <select
            value={provider}
            onChange={(event) => setProvider(event.target.value as Provider)}
            className={SELECT_CLASS}
          >
            {PROVIDERS.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
        <label className={LABEL_CLASS}>
          Model
          <Input
            type="text"
            value={model}
            onChange={(event) => setModel(event.target.value)}
            maxLength={100}
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
      </div>
      <label className={LABEL_CLASS}>
        API key
        <Input
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          maxLength={500}
          autoComplete="off"
          placeholder={
            hasKey ? "Key saved, leave empty to keep it" : "Paste your API key"
          }
          className={FIELD_HOVER}
        />
      </label>
      <Button
        type="submit"
        variant="outline"
        disabled={busy || model.trim() === ""}
      >
        {busy ? "Saving…" : "Save"}
      </Button>
      {message && (
        <p role="status" className="text-sm text-muted-foreground">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-destructive">
          {error}
        </p>
      )}
    </form>
  );
}
