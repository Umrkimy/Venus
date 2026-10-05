"use client";

import { useSyncExternalStore } from "react";

// Hands-free in the web: on = the browser mic always listens while this tab
// is in front, no "Hey Venus" needed. Remembered per browser.
const STORAGE_KEY = "venus.listen";

const listeners = new Set<() => void>();
// The mic is really open right now (on, tab in front, permission given).
let active = false;

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

// Storage can be blocked (private window, site data off); then it starts off.
function loadOn(): boolean {
  try {
    return localStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

export function setListenOn(on: boolean) {
  try {
    localStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    // Not remembered next visit.
  }
  listeners.forEach((listener) => listener());
}

// The server has no localStorage, so it always draws "off".
export function useListenOn(): boolean {
  return useSyncExternalStore(subscribe, loadOn, () => false);
}

// Read by the Core poll: the PC pauses "Hey Venus" while this is true,
// so you aren't answered twice.
export function isListeningActive(): boolean {
  return active;
}

export function setListeningActive(on: boolean) {
  active = on;
}
