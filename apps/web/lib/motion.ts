import type { Transition } from "motion/react";

// One feel for every animation, so later parts (the voice circle) match.
export const springSoft: Transition = { type: "spring", stiffness: 260, damping: 30 };

// Appear: fade in while rising a little.
export const fadeUp = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0 },
};
