"use client";

import { useState } from "react";

type TextCommandProps = {
  deviceId: string;
  disabled: boolean;
  onSend: (text: string) => void;
};

export default function TextCommand({
  deviceId,
  disabled,
  onSend,
}: TextCommandProps) {
  const [text, setText] = useState("");
  const inputId = `text-${deviceId}`;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSend(text.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="mt-3">
      <label htmlFor={inputId} className="sr-only">
        What to open on {deviceId}
      </label>
      <div className="flex gap-2">
        <input
          id={inputId}
          type="text"
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Tell Venus what to open, e.g. open notepad"
          autoComplete="off"
          className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent"
        />
        <button
          type="submit"
          disabled={disabled || text.trim() === ""}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
        >
          Go
        </button>
      </div>
    </form>
  );
}
