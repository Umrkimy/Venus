"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

const STORAGE_KEY = "venus.speak";

// Storage can be blocked (private window, site data off); then it just isn't remembered.
function loadOn(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

// Components showing the toggle; told when it flips.
const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function saveOn(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // Not remembered next visit (and the toggle can't turn on).
  }
  listeners.forEach((listener) => listener());
}

// Plays Luna's lines out loud when the speaker is on.
export function useSpeaker() {
  // The server has no localStorage, so it always draws "off".
  const on = useSyncExternalStore(subscribe, loadOn, () => false);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  // Stop talking if the chat closes mid-line.
  useEffect(() => {
    return () => audioRef.current?.pause();
  }, []);

  function stop() {
    const audio = audioRef.current;
    if (audio) {
      audio.pause();
      // Frees the mp3 the browser kept in memory.
      URL.revokeObjectURL(audio.src);
    }
    audioRef.current = null;
    setPlaying(false);
  }

  function toggle() {
    const next = !on;
    saveOn(next);
    setError(null);
    if (!next) stop();
  }

  async function speak(text: string) {
    if (!on) return;
    setError(null);
    try {
      const response = await fetch("/api/voice/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      if (!response.ok) {
        // e.g. "Voice reply needs a Fish Audio key": Core's words say what to do.
        const data = await response.json().catch(() => null);
        setError(data?.detail ?? "Couldn't say that out loud.");
        return;
      }
      const url = URL.createObjectURL(await response.blob());
      // A newer line wins: no two Lunas talking over each other.
      stop();
      const audio = new Audio(url);
      audioRef.current = audio;
      audio.onended = () => {
        if (audioRef.current === audio) stop();
      };
      setPlaying(true);
      // The browser can still refuse sound before any click on the page.
      await audio.play().catch(() => stop());
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    }
  }

  return { on, playing, error, toggle, speak, stop };
}
