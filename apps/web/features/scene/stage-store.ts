"use client";

import { useSyncExternalStore } from "react";

// The open part of the chat above the dialog box. The 3D camera listens to
// drags and zooms there, so the chat's own buttons and text stay clickable.
let stage: HTMLElement | null = null;
let reset: (() => void) | null = null;

const listeners = new Set<() => void>();

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function changed() {
  listeners.forEach((listener) => listener());
}

// The chat calls this with its stage element, and with null when it goes.
export function setStage(element: HTMLElement | null) {
  if (stage === element) return;
  stage = element;
  changed();
}

export function useStage(): HTMLElement | null {
  return useSyncExternalStore(subscribe, () => stage, () => null);
}

// The 3D scene says how to put the camera back; the chat's button calls it.
export function setResetView(action: (() => void) | null) {
  reset = action;
  changed();
}

export function useResetView(): (() => void) | null {
  return useSyncExternalStore(subscribe, () => reset, () => null);
}
