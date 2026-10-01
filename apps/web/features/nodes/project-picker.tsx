"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

type NodeProjects = { device_id: string; projects: string[] };

type ProjectPickerProps = {
  deviceId: string;
  disabled: boolean;
  onOpen: (projectName: string) => void;
};

export default function ProjectPicker({
  deviceId,
  disabled,
  onOpen,
}: ProjectPickerProps) {
  const [selected, setSelected] = useState("");

  const projects = useQuery({
    queryKey: ["projects", deviceId],
    queryFn: () =>
      getJson<NodeProjects>(
        `/api/nodes/${encodeURIComponent(deviceId)}/projects`,
      ),
  });

  const names = projects.data?.projects ?? [];
  const selectId = `project-${deviceId}`;

  if (projects.isError) {
    return (
      <p role="alert" className="mt-4 text-sm text-danger">
        Can&apos;t load projects from this PC.
      </p>
    );
  }

  // Few folders, so a plain drop-down is enough; hide it when there are none.
  if (projects.data && names.length === 0) {
    return <p className="mt-4 text-sm text-muted">No projects on this PC.</p>;
  }

  return (
    <div className="mt-4 flex gap-2">
      <label htmlFor={selectId} className="sr-only">
        Project to open in VS Code on {deviceId}
      </label>
      <select
        id={selectId}
        value={selected}
        onChange={(event) => setSelected(event.target.value)}
        disabled={projects.isPending}
        className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50"
      >
        <option value="">Open a project in VS Code…</option>
        {names.map((name) => (
          <option key={name} value={name}>
            {name}
          </option>
        ))}
      </select>
      <button
        type="button"
        onClick={() => onOpen(selected)}
        disabled={disabled || selected === ""}
        className="rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
      >
        Open project
      </button>
    </div>
  );
}
