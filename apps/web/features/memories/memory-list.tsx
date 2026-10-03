"use client";

import { useState } from "react";

import DeleteMemoryDialog from "./delete-memory-dialog";
import MemoryEditor from "./memory-editor";
import MemoryRow from "./memory-row";
import { type Memory, useMemories, useMemoryActions } from "./use-memories";

export default function MemoryList() {
  const memories = useMemories();
  const actions = useMemoryActions();
  const [deleting, setDeleting] = useState<Memory | null>(null);

  async function remove() {
    const memory = deleting;
    setDeleting(null);
    if (memory) await actions.remove(memory.id);
  }

  if (memories.isPending) {
    return (
      <div role="status">
        <span className="sr-only">Loading memories</span>
        <div className="h-24 rounded-lg bg-foreground/10 motion-safe:animate-pulse" />
      </div>
    );
  }

  if (memories.isError) {
    return (
      <p role="alert" className="text-sm text-destructive">
        Can&apos;t load memories.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <MemoryEditor initialText="" saveLabel="Add memory" onSave={actions.create} />
      {actions.error && (
        <p role="alert" className="text-sm text-destructive">
          {actions.error}
        </p>
      )}
      {memories.data.length === 0 ? (
        <p className="text-sm text-muted-foreground">
          Venus doesn&apos;t remember anything yet.
        </p>
      ) : (
        <ul className="space-y-2">
          {memories.data.map((memory) => (
            <MemoryRow
              key={memory.id}
              memory={memory}
              actions={actions}
              onDelete={setDeleting}
            />
          ))}
        </ul>
      )}
      <DeleteMemoryDialog
        memory={deleting}
        onCancel={() => setDeleting(null)}
        onConfirm={remove}
      />
    </div>
  );
}
