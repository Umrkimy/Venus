"use client";

import { useSyncExternalStore } from "react";

// The 3D Venus behind the chat. On unless turned off in Settings;
// remembered per browser, so a phone can be off while the PC is on.
const STORAGE_KEY = "venus.character";

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

// Storage can be blocked (private window, site data off); then she stays on.
function loadOn(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) !== "off";
  } catch {
    return true;
  }
}

export function setCharacterOn(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // Not remembered next visit.
  }
  listeners.forEach((listener) => listener());
}

// The server can't draw 3D, so it says "off"; the browser then decides.
export function useCharacterOn(): boolean {
  return useSyncExternalStore(subscribe, loadOn, () => false);
}
