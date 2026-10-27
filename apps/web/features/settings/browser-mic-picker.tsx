"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { saveBrowserMic, useBrowserMic } from "@/features/voice/browser-mic";

import { LABEL_CLASS, SELECT_TRIGGER_CLASS } from "./field-styles";

const DEFAULT_MIC = "default-mic";

// Which mic this browser uses when you talk to Venus here (phone or PC browser).
export default function BrowserMicPicker() {
  const micId = useId();
  const chosen = useBrowserMic();
  const [error, setError] = useState<string | null>(null);
  const devices = useQuery({
    queryKey: ["browser-mics"],
    queryFn: async () => {
      if (!navigator.mediaDevices?.enumerateDevices) return [];
      const all = await navigator.mediaDevices.enumerateDevices();
      return all.filter((device) => device.kind === "audioinput" && device.deviceId !== "default");
    },
  });
  const mics = devices.data ?? null;
  const { refetch } = devices;

  useEffect(() => {
    const changed = () => refetch();
    navigator.mediaDevices?.addEventListener("devicechange", changed);
    return () => navigator.mediaDevices?.removeEventListener("devicechange", changed);
  }, [refetch]);

  // Browsers hide mic names until the page may use the mic.
  const named = mics?.some((mic) => mic.label) ?? false;

  async function showNames() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.getTracks().forEach((track) => track.stop());
      setError(null);
      await refetch();
    } catch {
      setError("The browser blocked the mic. Allow it in the address bar, then try again.");
    }
  }

  if (mics !== null && mics.length === 0) {
    return <p className="text-sm text-muted-foreground">This browser can&apos;t list its mics.</p>;
  }

  return (
    <div>
      <label htmlFor={micId} className={LABEL_CLASS}>
        Mic in this browser
      </label>
      {named ? (
        <Select value={chosen || DEFAULT_MIC} onValueChange={(value) => saveBrowserMic(value === DEFAULT_MIC ? "" : value)}>
          <SelectTrigger id={micId} className={SELECT_TRIGGER_CLASS}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={DEFAULT_MIC}>Default mic</SelectItem>
            {mics?.map((mic, index) => (
              <SelectItem key={mic.deviceId} value={mic.deviceId}>
                {mic.label || `Mic ${index + 1}`}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : (
        <div className="mt-2">
          <Button id={micId} type="button" variant="outline" size="sm" onClick={showNames}>
            Show my mics
          </Button>
        </div>
      )}
      <p className="mt-1 text-sm text-muted-foreground">
        For hands-free talking on this device. Some browsers type your live words with the system&apos;s default mic.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
