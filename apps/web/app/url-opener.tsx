"use client";

import { useState } from "react";

type UrlOpenerProps = {
  deviceId: string;
  disabled: boolean;
  onOpen: (url: string) => void;
};

// Turns "youtube.com" into "https://youtube.com"; null for anything not http(s).
function toWebUrl(text: string): string | null {
  const trimmed = text.trim();
  if (trimmed === "") return null;
  const withScheme = trimmed.includes("://") ? trimmed : `https://${trimmed}`;
  try {
    const url = new URL(withScheme);
    return url.protocol === "https:" || url.protocol === "http:"
      ? url.href
      : null;
  } catch {
    return null;
  }
}

export default function UrlOpener({
  deviceId,
  disabled,
  onOpen,
}: UrlOpenerProps) {
  const [text, setText] = useState("");
  const [invalid, setInvalid] = useState(false);
  const inputId = `url-${deviceId}`;

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const url = toWebUrl(text);
    if (url === null) {
      setInvalid(true);
      return;
    }
    setInvalid(false);
    onOpen(url);
  }

  return (
    <form onSubmit={handleSubmit} className="mt-4">
      <label htmlFor={inputId} className="sr-only">
        Link to open on {deviceId}
      </label>
      <div className="flex gap-2">
        <input
          id={inputId}
          type="text"
          inputMode="url"
          value={text}
          onChange={(event) => {
            setText(event.target.value);
            setInvalid(false);
          }}
          placeholder="Open a link, e.g. youtube.com"
          autoComplete="off"
          aria-invalid={invalid}
          className="min-w-0 flex-1 rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent"
        />
        <button
          type="submit"
          disabled={disabled || text.trim() === ""}
          className="rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]"
        >
          Open link
        </button>
      </div>
      {invalid && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Enter a web link, like youtube.com.
        </p>
      )}
    </form>
  );
}
