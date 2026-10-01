"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

export type NodeApp = { name: string; app_id: string };
type NodeApps = { device_id: string; apps: NodeApp[] };

// Enough to find an app without a long scrolling list.
const MAX_MATCHES = 8;

type AppPickerProps = {
  deviceId: string;
  disabled: boolean;
  onOpen: (app: NodeApp) => void;
};

export default function AppPicker({ deviceId, disabled, onOpen }: AppPickerProps) {
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<NodeApp | null>(null);

  const apps = useQuery({
    queryKey: ["apps", deviceId],
    queryFn: () =>
      getJson<NodeApps>(`/api/nodes/${encodeURIComponent(deviceId)}/apps`),
  });

  // Worked out on every render from the search text; no extra state.
  const text = search.trim().toLowerCase();
  const matches =
    text === ""
      ? []
      : (apps.data?.apps ?? [])
          .filter((app) => app.name.toLowerCase().includes(text))
          .slice(0, MAX_MATCHES);
  const inputId = `app-search-${deviceId}`;

  return (
    <div className="mt-3">
      <label htmlFor={inputId} className="sr-only">
        Search apps on {deviceId}
      </label>
      <input
        id={inputId}
        type="search"
        value={search}
        onChange={(event) => {
          setSearch(event.target.value);
          setSelected(null);
        }}
        placeholder="Search apps, e.g. Notepad"
        autoComplete="off"
        className="w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent"
      />

      {apps.isError && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Can&apos;t load apps from this PC.
        </p>
      )}

      {text !== "" && apps.data && matches.length === 0 && (
        <p className="mt-2 text-sm text-muted">No app matches that name.</p>
      )}

      {matches.length > 0 && (
        <ul className="mt-2 space-y-1">
          {matches.map((app) => {
            const isSelected = selected?.app_id === app.app_id;
            return (
              <li key={app.app_id}>
                <button
                  type="button"
                  onClick={() => setSelected(app)}
                  aria-pressed={isSelected}
                  className={`w-full rounded-md px-3 py-2 text-left text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent ${
                    isSelected ? "bg-accent/15 font-medium" : "hover:bg-muted/10"
                  }`}
                >
                  {app.name}
                </button>
              </li>
            );
          })}
        </ul>
      )}

      <button
        type="button"
        onClick={() => selected && onOpen(selected)}
        disabled={disabled || selected === null}
        className="mt-3 rounded-md bg-accent px-3 py-1.5 text-sm font-medium text-accent-foreground outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
      >
        {selected ? `Open ${selected.name}` : "Open"}
      </button>
    </div>
  );
}
