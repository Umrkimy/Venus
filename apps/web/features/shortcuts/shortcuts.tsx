"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

type Shortcut = {
  keyword: string;
  label: string;
  home_url: string;
  search_url: string | null;
};
type ShortcutsResponse = { shortcuts: Shortcut[] };

// Same look for every text box and every border-style button.
const INPUT_CLASS =
  "mt-1 w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent";
const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]";

export default function Shortcuts() {
  const [keyword, setKeyword] = useState("");
  const [label, setLabel] = useState("");
  const [homeUrl, setHomeUrl] = useState("");
  const [searchUrl, setSearchUrl] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const shortcuts = useQuery({
    queryKey: ["shortcuts"],
    queryFn: () => getJson<ShortcutsResponse>("/api/shortcuts"),
  });

  async function add(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const response = await fetch("/api/shortcuts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          keyword,
          label,
          home_url: homeUrl,
          search_url: searchUrl.trim() || null,
        }),
      });
      const data = await response.json();
      if (!response.ok) {
        // Core's own messages are strings; field errors come as a list.
        setError(
          typeof data.detail === "string" ? data.detail : "Check the fields.",
        );
        return;
      }
      setKeyword("");
      setLabel("");
      setHomeUrl("");
      setSearchUrl("");
      await shortcuts.refetch();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  async function remove(name: string) {
    setBusy(true);
    setError(null);
    try {
      // 204 has an empty body, so no response.json() here.
      const response = await fetch(`/api/shortcuts/${name}`, {
        method: "DELETE",
      });
      if (!response.ok) {
        setError("Couldn't delete that shortcut.");
        return;
      }
      await shortcuts.refetch();
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="mt-10">
      <h2 className="text-sm font-medium text-muted">Shortcuts</h2>

      {shortcuts.isPending && (
        <div role="status" className="mt-2">
          <span className="sr-only">Loading shortcuts</span>
          <div className="h-12 w-full rounded-md bg-muted/20 motion-safe:animate-pulse" />
        </div>
      )}

      {shortcuts.isError && (
        <p role="alert" className="mt-2 text-sm text-danger">
          Can&apos;t load shortcuts.
        </p>
      )}

      {shortcuts.isSuccess && shortcuts.data.shortcuts.length === 0 && (
        <p className="mt-2 text-sm text-muted">No shortcuts yet.</p>
      )}

      {shortcuts.isSuccess && shortcuts.data.shortcuts.length > 0 && (
        <ul className="mt-2 space-y-2">
          {shortcuts.data.shortcuts.map((shortcut) => (
            <li
              key={shortcut.keyword}
              className="flex items-start justify-between gap-3 rounded-md border border-border px-4 py-3"
            >
              <div className="min-w-0">
                <p className="font-medium">
                  {shortcut.keyword}{" "}
                  <span className="font-normal text-muted">
                    {shortcut.label}
                  </span>
                </p>
                <p className="break-all text-xs text-muted">
                  {shortcut.home_url}
                </p>
                {shortcut.search_url && (
                  <p className="break-all text-xs text-muted">
                    {shortcut.search_url}
                  </p>
                )}
              </div>
              <button
                type="button"
                disabled={busy}
                onClick={() => remove(shortcut.keyword)}
                className={BUTTON_CLASS}
              >
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={add} className="mt-4 space-y-3">
        <label className="block text-sm">
          Keyword
          <input
            type="text"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            placeholder="comix"
            autoComplete="off"
            className={INPUT_CLASS}
          />
        </label>
        <label className="block text-sm">
          Name
          <input
            type="text"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Comix"
            autoComplete="off"
            className={INPUT_CLASS}
          />
        </label>
        <label className="block text-sm">
          Home link
          <input
            type="text"
            inputMode="url"
            value={homeUrl}
            onChange={(event) => setHomeUrl(event.target.value)}
            placeholder="https://site.com"
            autoComplete="off"
            className={INPUT_CLASS}
          />
        </label>
        <label className="block text-sm">
          Search link (optional)
          <input
            type="text"
            inputMode="url"
            value={searchUrl}
            onChange={(event) => setSearchUrl(event.target.value)}
            placeholder="https://site.com/search?q={words}"
            autoComplete="off"
            className={INPUT_CLASS}
          />
        </label>
        <button
          type="submit"
          disabled={busy || !keyword.trim() || !label.trim() || !homeUrl.trim()}
          className={BUTTON_CLASS}
        >
          Add shortcut
        </button>
      </form>

      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </section>
  );
}
