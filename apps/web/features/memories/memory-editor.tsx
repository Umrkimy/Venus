"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

import { TEXT_LIMIT } from "./use-memories";

type MemoryEditorProps = {
  initialText: string;
  saveLabel: string;
  // Resolves true when saved, so the caller can close or clear the editor.
  onSave: (text: string) => Promise<boolean>;
  onCancel?: () => void;
};

// One text box for a fact, used to add a new memory and to edit an old one.
export default function MemoryEditor({
  initialText,
  saveLabel,
  onSave,
  onCancel,
}: MemoryEditorProps) {
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    const saved = await onSave(text.trim());
    setBusy(false);
    // A new memory box empties after saving so the next fact can go in.
    if (saved && !onCancel) setText("");
  }

  return (
    <form onSubmit={submit} className="space-y-2">
      <Textarea
        value={text}
        onChange={(event) => setText(event.target.value)}
        maxLength={TEXT_LIMIT}
        rows={2}
        aria-label="Memory"
        placeholder="e.g. My favourite colour is red"
        className="hover:border-foreground/40"
      />
      <div className="flex items-center gap-2">
        <Button type="submit" variant="outline" size="sm" disabled={busy || text.trim() === ""}>
          {busy ? "Saving…" : saveLabel}
        </Button>
        {onCancel && (
          <Button type="button" variant="ghost" size="sm" onClick={onCancel} disabled={busy}>
            Cancel
          </Button>
        )}
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
          {text.length} / {TEXT_LIMIT}
        </span>
      </div>
    </form>
  );
}
