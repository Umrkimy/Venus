"use client";

import { Monitor, Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";
import { useSyncExternalStore } from "react";

const OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "dark", label: "Dark", icon: Moon },
  { value: "system", label: "System", icon: Monitor },
];

// False on the server, true in the browser. The saved theme is only known
// in the browser, so the switch waits for it instead of guessing.
const subscribe = () => () => {};
function useInBrowser() {
  return useSyncExternalStore(subscribe, () => true, () => false);
}

export default function ThemeSwitch() {
  const { theme, setTheme } = useTheme();
  const inBrowser = useInBrowser();
  const current = inBrowser ? theme : undefined;

  return (
    <div>
      <div
        role="group"
        aria-label="Theme"
        className="inline-flex rounded-lg border border-border bg-muted/50 p-1"
      >
        {OPTIONS.map(({ value, label, icon: Icon }) => {
          const active = value === current;
          return (
            <button
              key={value}
              type="button"
              aria-pressed={active}
              onClick={() => setTheme(value)}
              className={`inline-flex items-center gap-1.5 rounded-md px-4 py-1.5 text-sm font-medium outline-none transition-colors focus-visible:ring-2 focus-visible:ring-ring ${
                active
                  ? "bg-primary text-primary-foreground shadow-xs"
                  : "text-muted-foreground hover:bg-background hover:text-foreground"
              }`}
            >
              <Icon aria-hidden="true" className="size-4" />
              {label}
            </button>
          );
        })}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        System follows your Windows setting. Saved in this browser.
      </p>
    </div>
  );
}
