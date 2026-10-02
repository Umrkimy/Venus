"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

type Provider = "fake" | "openai";
type LlmResponse = { provider: Provider; model: string; has_key: boolean };

const PROVIDERS: Provider[] = ["fake", "openai"];

const INPUT_CLASS =
  "mt-1 w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent";
const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]";

export default function LlmSettings() {
  const llm = useQuery({
    queryKey: ["llm"],
    queryFn: () => getJson<LlmResponse>("/api/settings/llm"),
  });

  if (llm.isPending) {
    return (
      <div role="status" className="mt-4">
        <span className="sr-only">Loading LLM settings</span>
        <div className="h-8 w-36 rounded-md bg-muted/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (llm.isError) {
    return (
      <p role="alert" className="mt-4 text-sm text-danger">
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
    <form onSubmit={save} className="mt-6 space-y-3">
      <h2 className="text-sm font-medium text-muted">AI model</h2>
      <label className="block text-sm">
        Provider
        <select
          value={provider}
          onChange={(event) => setProvider(event.target.value as Provider)}
          className={INPUT_CLASS}
        >
          {PROVIDERS.map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </label>
      <label className="block text-sm">
        Model
        <input
          type="text"
          value={model}
          onChange={(event) => setModel(event.target.value)}
          maxLength={100}
          autoComplete="off"
          className={INPUT_CLASS}
        />
      </label>
      <label className="block text-sm">
        API key
        <input
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          maxLength={500}
          autoComplete="off"
          placeholder={
            hasKey ? "Key saved, leave empty to keep it" : "Paste your API key"
          }
          className={INPUT_CLASS}
        />
      </label>
      <button
        type="submit"
        disabled={busy || model.trim() === ""}
        className={BUTTON_CLASS}
      >
        Save
      </button>
      {message && (
        <p role="status" className="text-sm text-muted">
          {message}
        </p>
      )}
      {error && (
        <p role="alert" className="text-sm text-danger">
          {error}
        </p>
      )}
    </form>
  );
}
