"use client";

import { useSyncExternalStore } from "react";

// Which mic this browser records you with. Saved per device: a phone and a PC have different mics.
const STORAGE_KEY = "venus.browserMic";
const listeners = new Set<() => void>();

export function browserMicId(): string {
  try {
    return localStorage.getItem(STORAGE_KEY) ?? "";
  } catch {
    return "";
  }
}

export function saveBrowserMic(id: string) {
  try {
    if (id) localStorage.setItem(STORAGE_KEY, id);
    else localStorage.removeItem(STORAGE_KEY);
  } catch {
    // Storage blocked: the default mic stays.
  }
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useBrowserMic(): string {
  return useSyncExternalStore(subscribe, browserMicId, () => "");
}

const VOICE = { echoCancellation: true, noiseSuppression: true, autoGainControl: true };

// The chosen mic, or the default one if it was unplugged since.
export async function openBrowserMic(): Promise<MediaStream> {
  const id = browserMicId();
  if (id) {
    try {
      return await navigator.mediaDevices.getUserMedia({ audio: { ...VOICE, deviceId: { exact: id } } });
    } catch (exc) {
      if (!(exc instanceof DOMException) || !["OverconstrainedError", "NotFoundError"].includes(exc.name)) throw exc;
    }
  }
  return navigator.mediaDevices.getUserMedia({ audio: VOICE });
}
