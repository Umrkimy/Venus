"use client";

import { useQuery } from "@tanstack/react-query";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useReadingSettings } from "@/features/chat/reading-settings";
import { getJson } from "@/lib/get-json";

import { FIELD_HOVER, LABEL_CLASS, SELECT_CLASS } from "./field-styles";

type FishModel = "s2.1-pro-free" | "s2.1-pro" | "s2-pro" | "s1";
type VoiceResponse = { voice_id: string; model: FishModel; has_key: boolean };

const MODELS: { value: FishModel; label: string }[] = [
  { value: "s2.1-pro-free", label: "s2.1-pro-free (free)" },
  { value: "s2.1-pro", label: "s2.1-pro (paid)" },
  { value: "s2-pro", label: "s2-pro (paid)" },
  { value: "s1", label: "s1 (paid)" },
];

const TEST_LINE = "Hi, it's Luna. This is how I sound.";

export default function VoiceSettings() {
  const voice = useQuery({
    queryKey: ["voice"],
    queryFn: () => getJson<VoiceResponse>("/api/settings/voice"),
  });

  if (voice.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading voice settings</span>
        <div className="h-8 w-36 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (voice.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load the voice settings.
      </p>
    );
  }

  return <VoiceForm initial={voice.data} />;
}

function VoiceForm({ initial }: { initial: VoiceResponse }) {
  const { volume } = useReadingSettings();
  const [voiceId, setVoiceId] = useState(initial.voice_id);
  const [model, setModel] = useState<FishModel>(initial.model);
  const [apiKey, setApiKey] = useState("");
  const [hasKey, setHasKey] = useState(initial.has_key);
  const [busy, setBusy] = useState(false);
  const [testing, setTesting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    setError(null);

    // Leave api_key out when the box is empty so Core keeps the saved key.
    const body: { voice_id: string; model: FishModel; api_key?: string } = {
      voice_id: voiceId.trim(),
      model,
    };
    if (apiKey) body.api_key = apiKey;

    try {
      const response = await fetch("/api/settings/voice", {
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
        setError("Saving voice settings failed.");
        return;
      }
      const saved: VoiceResponse = await response.json();
      setHasKey(saved.has_key);
      setMessage(`Saved: ${saved.model}${apiKey ? ", key updated" : ""}`);
      setApiKey("");
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  // Asks Fish fresh each time (no cache), so you hear what you just saved.
  async function testVoice() {
    setTesting(true);
    setMessage(null);
    setError(null);
    audioRef.current?.pause();
    try {
      const response = await fetch("/api/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: TEST_LINE }),
      });
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Couldn't play the test line.");
        return;
      }
      const url = URL.createObjectURL(await response.blob());
      const audio = new Audio(url);
      audio.volume = volume;
      audio.onended = () => URL.revokeObjectURL(url);
      audioRef.current = audio;
      await audio.play();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setTesting(false);
    }
  }

  return (
    <form onSubmit={save} className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className={LABEL_CLASS}>
          Voice id
          <Input
            type="text"
            value={voiceId}
            onChange={(event) => setVoiceId(event.target.value)}
            maxLength={100}
            autoComplete="off"
            placeholder="Empty: Fish picks a voice"
            className={FIELD_HOVER}
          />
          <span className="mt-1 block text-xs font-normal text-muted-foreground">
            The id at the end of the voice&apos;s fish.audio link.
          </span>
        </label>
        <label className={LABEL_CLASS}>
          Model
          <select
            value={model}
            onChange={(event) => setModel(event.target.value as FishModel)}
            className={SELECT_CLASS}
          >
            {MODELS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>
      <label className={LABEL_CLASS}>
        Fish Audio API key
        <Input
          type="password"
          value={apiKey}
          onChange={(event) => setApiKey(event.target.value)}
          maxLength={500}
          autoComplete="off"
          placeholder={
            hasKey ? "Key saved, leave empty to keep it" : "Paste your Fish Audio API key"
          }
          className={FIELD_HOVER}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" variant="outline" disabled={busy}>
          {busy ? "Saving…" : "Save"}
        </Button>
        <Button
          type="button"
          variant="ghost"
          onClick={() => void testVoice()}
          disabled={testing || !hasKey}
        >
          {testing ? "Asking Luna…" : "Test voice"}
        </Button>
      </div>
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
