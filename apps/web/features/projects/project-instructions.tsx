"use client";

import { Pencil } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { type Project, useProjectActions } from "@/features/projects/use-projects";

const INSTRUCTIONS_LIMIT = 4000;

// The project's extra rules for Venus; Edit opens a text box in place.
export default function ProjectInstructions({ project }: { project: Project }) {
  const actions = useProjectActions();
  const [editing, setEditing] = useState(false);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  function startEditing() {
    setText(project.instructions ?? "");
    setEditing(true);
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    // An empty box clears the instructions.
    if (await actions.setInstructions(project.id, text)) setEditing(false);
    setBusy(false);
  }

  return (
    <div className="mt-3 rounded-lg border border-border p-3">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-medium">Instructions</h2>
        {!editing && (
          <Button variant="ghost" size="xs" onClick={startEditing} className="ml-auto">
            <Pencil />
            Edit
          </Button>
        )}
      </div>
      {editing ? (
        <form onSubmit={save} className="mt-2 space-y-2">
          <Textarea
            value={text}
            onChange={(event) => setText(event.target.value)}
            maxLength={INSTRUCTIONS_LIMIT}
            rows={4}
            aria-label="Instructions"
            placeholder="e.g. I'm studying for my databases exam. Explain step by step."
            className="hover:border-foreground/40"
          />
          <div className="flex items-center gap-2">
            <Button type="submit" variant="outline" size="sm" disabled={busy}>
              {busy ? "Saving…" : "Save"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => setEditing(false)}
              disabled={busy}
            >
              Cancel
            </Button>
            <span className="ml-auto text-xs text-muted-foreground tabular-nums">
              {text.length} / {INSTRUCTIONS_LIMIT}
            </span>
          </div>
        </form>
      ) : (
        <p className="mt-1 line-clamp-3 text-sm whitespace-pre-line text-muted-foreground">
          {project.instructions ??
            "No instructions yet. Venus follows these in every chat in this project."}
        </p>
      )}
      {actions.error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {actions.error}
        </p>
      )}
    </div>
  );
}
