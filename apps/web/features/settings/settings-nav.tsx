"use client";

import {
  Archive,
  AudioLines,
  Brain,
  ChartColumn,
  Heart,
  Link2,
  MonitorSmartphone,
  SlidersHorizontal,
  Sparkles,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import { cn } from "@/lib/utils";

const PAGES = [
  { href: "/settings/general", label: "General", icon: SlidersHorizontal },
  { href: "/settings/personality", label: "Personality", icon: Heart },
  { href: "/settings/memory", label: "Memory", icon: Brain },
  { href: "/settings/ai", label: "AI model", icon: Sparkles },
  { href: "/settings/usage", label: "Usage", icon: ChartColumn },
  { href: "/settings/voice", label: "Voice", icon: AudioLines },
  { href: "/settings/shortcuts", label: "Shortcuts", icon: Link2 },
  { href: "/settings/devices", label: "Devices", icon: MonitorSmartphone },
  { href: "/settings/archive", label: "Archive", icon: Archive },
];

// A row along the top on a phone, a column on the left on a computer.
export default function SettingsNav() {
  const pathname = usePathname();

  return (
    <nav
      aria-label="Settings"
      className="flex shrink-0 gap-1 overflow-x-auto md:w-48 md:flex-col"
    >
      {PAGES.map((page) => {
        // A capital letter lets JSX draw the icon stored in the variable.
        const Icon = page.icon;
        const active = pathname === page.href;
        return (
          <Link
            key={page.href}
            href={page.href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm transition-colors",
              active
                ? "bg-muted font-medium text-foreground"
                : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )}
          >
            <Icon className="size-4" />
            {page.label}
          </Link>
        );
      })}
    </nav>
  );
}
