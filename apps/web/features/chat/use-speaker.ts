"use client";

import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { useReadingSettings } from "./reading-settings";
import { splitSentences } from "./split-lines";

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

// Where Luna is in a message: the words on screen follow this.
export type Speaking = {
  // The message's position in the chat.
  id: number;
  lines: string[];
  // The line playing now, and how far through it (0 to 1).
  line: number;
  fraction: number;
  // First time the words type along; a replay leaves the text as it is.
  typing: boolean;
};

// Core said why it couldn't speak, e.g. "Voice reply needs a Fish Audio key".
class VoiceError extends Error {}

async function fetchLine(text: string): Promise<Blob> {
  const response = await fetch("/api/voice/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: text.trim() }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new VoiceError(data?.detail ?? "Couldn't say that out loud.");
  }
  return response.blob();
}

// Says Luna's replies line by line, like a visual novel.
export function useSpeaker() {
  // The server has no localStorage, so it always draws "off".
  const on = useSyncExternalStore(subscribe, loadOn, () => false);
  const { volume } = useReadingSettings();
  const [speaking, setSpeaking] = useState<Speaking | null>(null);
  const [error, setError] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  // Ends the line playing now (its promise resolves).
  const finishRef = useRef<((ended: boolean) => void) | null>(null);
  // Every play gets a new number; an older play sees it changed and quits.
  const runRef = useRef(0);
  // Each message's audio, line by line, kept for this visit so replays are free.
  const cacheRef = useRef(new Map<number, (Promise<Blob> | undefined)[]>());

  // Stop talking if the chat closes mid-line.
  useEffect(() => {
    const run = runRef;
    const finish = finishRef;
    return () => {
      run.current += 1;
      finish.current?.(false);
    };
  }, []);

  function stop() {
    runRef.current += 1;
    finishRef.current?.(false);
    setSpeaking(null);
  }

  function toggle() {
    const next = !on;
    saveOn(next);
    setError(null);
    if (!next) stop();
  }

  // Plays one mp3. True when it played to the end; false when stopped or blocked.
  function playLine(blob: Blob, onProgress: (fraction: number) => void) {
    return new Promise<boolean>((resolve) => {
      const audio = new Audio(URL.createObjectURL(blob));
      audio.volume = volume;
      audioRef.current = audio;
      let frame = 0;
      const finish = (ended: boolean) => {
        cancelAnimationFrame(frame);
        audio.pause();
        // Frees the mp3 the browser kept in memory (the Blob stays cached).
        URL.revokeObjectURL(audio.src);
        if (audioRef.current === audio) audioRef.current = null;
        if (finishRef.current === finish) finishRef.current = null;
        resolve(ended);
      };
      finishRef.current = finish;
      const tick = () => {
        if (audio.duration) onProgress(audio.currentTime / audio.duration);
        frame = requestAnimationFrame(tick);
      };
      audio.onended = () => finish(true);
      // The browser can refuse sound before any click on the page.
      audio.play().then(
        () => {
          frame = requestAnimationFrame(tick);
        },
        () => finish(false),
      );
    });
  }

  async function play(id: number, text: string, typing: boolean) {
    // A newer line wins: no two Lunas talking over each other.
    finishRef.current?.(false);
    const run = ++runRef.current;
    setError(null);

    const lines = splitSentences(text);
    if (lines.length === 0) {
      setSpeaking(null);
      return;
    }
    const audio = cacheRef.current.get(id) ?? [];
    cacheRef.current.set(id, audio);
    const load = (index: number) => {
      let line = audio[index];
      if (!line) {
        line = fetchLine(lines[index]);
        audio[index] = line;
        // A failed line is asked for again next time.
        line.catch(() => {
          audio[index] = undefined;
        });
      }
      return line;
    };
    const show = (line: number, fraction: number) => {
      if (run === runRef.current) setSpeaking({ id, lines, line, fraction, typing });
    };

    // Set before anything waits, so new words start hidden instead of flashing.
    show(0, 0);
    for (let index = 0; index < lines.length; index++) {
      let blob: Blob;
      try {
        blob = await load(index);
      } catch (problem) {
        if (run !== runRef.current) return;
        setError(
          problem instanceof VoiceError
            ? problem.message
            : "Can't reach Venus Core. Is it running?",
        );
        // The rest of the words show at once instead of getting stuck.
        setSpeaking(null);
        return;
      }
      if (run !== runRef.current) return;
      // Make the next line while this one plays.
      if (index + 1 < lines.length) load(index + 1).catch(() => {});
      show(index, 0);
      const ended = await playLine(blob, (fraction) => show(index, fraction));
      if (run !== runRef.current) return;
      if (!ended) {
        setSpeaking(null);
        return;
      }
      show(index, 1);
    }
    setSpeaking(null);
  }

  // A new reply: only when the speaker is on.
  function speak(id: number, text: string) {
    if (on) void play(id, text, true);
  }

  // The replay button: even with the speaker off, you asked for it.
  function replay(id: number, text: string) {
    void play(id, text, false);
  }

  return { on, speaking, error, toggle, speak, replay, stop };
}
