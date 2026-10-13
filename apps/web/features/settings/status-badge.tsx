import { cn } from "@/lib/utils";

type Tone = "on" | "off" | "warn";

const STYLES: Record<Tone, string> = {
  on: "bg-emerald-500/12 text-emerald-700 dark:text-emerald-400",
  off: "bg-muted text-muted-foreground",
  warn: "bg-amber-500/15 text-amber-700 dark:text-amber-400",
};
const DOTS: Record<Tone, string> = { on: "bg-emerald-500", off: "bg-muted-foreground/50", warn: "bg-amber-500" };

// "Connected" in green, "Not connected" in grey: the state is the first thing you see.
export default function StatusBadge({ tone, children }: { tone: Tone; children: React.ReactNode }) {
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium", STYLES[tone])}>
      <span className={cn("size-1.5 rounded-full", DOTS[tone])} aria-hidden="true" />
      {children}
    </span>
  );
}
