"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";

import { NAME_LIMIT, TEXT_LIMIT } from "./use-personalities";

type PersonalityEditorProps = {
  initialName: string;
  initialText: string;
  // Resolves true when saved, so the card can close the editor.
  onSave: (name: string, text: string) => Promise<boolean>;
  onCancel: () => void;
};

// The name box and the big text box, used for new and existing personalities.
export default function PersonalityEditor({
  initialName,
  initialText,
  onSave,
  onCancel,
}: PersonalityEditorProps) {
  const [name, setName] = useState(initialName);
  const [text, setText] = useState(initialText);
  const [busy, setBusy] = useState(false);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    await onSave(name.trim(), text);
    setBusy(false);
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <label className={LABEL_CLASS}>
        Name
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={NAME_LIMIT}
          placeholder="e.g. Demo"
          autoComplete="off"
          className={FIELD_HOVER}
        />
      </label>
      <label className={LABEL_CLASS}>
        Who Venus is
        <Textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          maxLength={TEXT_LIMIT}
          rows={6}
          placeholder="You are Venus, ..."
          className="mt-1.5 hover:border-foreground/40"
        />
      </label>
      <div className="flex items-center gap-2">
        <Button type="submit" variant="outline" disabled={busy || name.trim() === ""}>
          {busy ? "Saving…" : "Save"}
        </Button>
        <Button type="button" variant="ghost" onClick={onCancel} disabled={busy}>
          Cancel
        </Button>
        <span className="ml-auto text-xs text-muted-foreground tabular-nums">
          {text.length} / {TEXT_LIMIT}
        </span>
      </div>
    </form>
  );
}
