"use client";

import { useSyncExternalStore } from "react";

export type ReadingSettings = {
  // Letters per second when Luna's words type out without voice.
  textSpeed: number;
  // 0 to 1.
  volume: number;
  // Skip typing: replies show all at once.
  instantText: boolean;
};

export const DEFAULT_READING: ReadingSettings = {
  textSpeed: 40,
  volume: 1,
  instantText: false,
};

const STORAGE_KEY = "venus.reading";

const listeners = new Set<() => void>();

// React compares snapshots by reference, so hand back the same object until storage changes.
let cachedRaw: string | null = null;
let cached = DEFAULT_READING;

function readStorage(): string | null {
  try {
    return localStorage.getItem(STORAGE_KEY);
  } catch {
    return null;
  }
}

function load(): ReadingSettings {
  const raw = readStorage();
  if (raw === cachedRaw) return cached;
  cachedRaw = raw;
  try {
    cached = raw ? { ...DEFAULT_READING, ...JSON.parse(raw) } : DEFAULT_READING;
  } catch {
    cached = DEFAULT_READING;
  }
  return cached;
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function saveReading(change: Partial<ReadingSettings>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...load(), ...change }));
  } catch {
    // Storage blocked: the defaults stay.
  }
  listeners.forEach((listener) => listener());
}

// The server has no localStorage, so it draws the defaults.
export function useReadingSettings(): ReadingSettings {
  return useSyncExternalStore(subscribe, load, () => DEFAULT_READING);
}
