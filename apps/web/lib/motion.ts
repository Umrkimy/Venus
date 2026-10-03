import type { Transition } from "motion/react";

// One feel for every animation, so later parts (the voice circle) match.
export const springSoft: Transition = { type: "spring", stiffness: 260, damping: 30 };

// Appear: fade in while rising a little.
export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
};

// Messages from a reopened chat appear one after another, capped so long chats don't crawl.
export function staggerDelay(index: number, step = 0.03, max = 10): number {
  return Math.min(index, max) * step;
}
