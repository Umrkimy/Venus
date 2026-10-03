"use client";

import { motion } from "motion/react";
import type { ReactNode } from "react";

// Unlike layout.tsx, a template mounts again on every page change,
// so this fade plays each time you switch pages.
export default function OwnerTemplate({ children }: { children: ReactNode }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.2, ease: "easeOut" }}
      className="flex min-h-0 flex-1 flex-col"
    >
      {children}
    </motion.div>
  );
}
