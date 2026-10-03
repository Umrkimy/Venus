"use client";

import { Pencil, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";

import MemoryEditor from "./memory-editor";
import type { Memory, useMemoryActions } from "./use-memories";

type MemoryRowProps = {
  memory: Memory;
  actions: ReturnType<typeof useMemoryActions>;
  onDelete: (memory: Memory) => void;
};

// Shows one fact; Edit turns the same row into the editor.
export default function MemoryRow({ memory, actions, onDelete }: MemoryRowProps) {
  const [editing, setEditing] = useState(false);

  async function save(text: string) {
    const saved = await actions.update(memory.id, text);
    if (saved) setEditing(false);
    return saved;
  }

  return (
    <li className="rounded-lg border border-border p-3">
      {editing ? (
        <MemoryEditor
          initialText={memory.text}
          saveLabel="Save"
          onSave={save}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <div className="flex items-start gap-2">
          <div className="min-w-0 flex-1">
            <p className="text-sm break-words whitespace-pre-line">{memory.text}</p>
            <p className="mt-1 text-xs text-muted-foreground">
              {new Date(memory.created_at).toLocaleDateString()}
            </p>
          </div>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Edit memory"
            onClick={() => setEditing(true)}
            className="text-muted-foreground"
          >
            <Pencil />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="Delete memory"
            onClick={() => onDelete(memory)}
            className="text-muted-foreground hover:text-destructive"
          >
            <Trash2 />
          </Button>
        </div>
      )}
    </li>
  );
}
