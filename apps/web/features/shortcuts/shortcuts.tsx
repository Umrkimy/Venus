"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { getJson } from "@/lib/get-json";

import ShortcutRow from "./shortcut-row";

export type Shortcut = {
  keyword: string;
  label: string;
  home_url: string;
  search_url: string | null;
};
type ShortcutsResponse = { shortcuts: Shortcut[] };

// Same look for every text box and every border-style button.
const INPUT_CLASS =
  "mt-1 w-full rounded-md border border-border bg-transparent px-3 py-2 text-sm outline-none placeholder:text-muted focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50";
const BUTTON_CLASS =
  "rounded-md border border-border px-3 py-1.5 text-sm font-medium outline-none focus-visible:ring-2 focus-visible:ring-accent disabled:opacity-50 motion-safe:transition-transform motion-safe:active:scale-[0.98]";

export default function Shortcuts() {
  const [keyword, setKeyword] = useState("");
  const [label, setLabel] = useState("");
  const [homeUrl, setHomeUrl] = useState("");
  const [searchExample, setSearchExample] = useState("");
  const [searchWords, setSearchWords] = useState("");
  // The keyword being edited, or null when the form adds a new shortcut.
  const [editing, setEditing] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const shortcuts = useQuery({
    queryKey: ["shortcuts"],
    queryFn: () => getJson<ShortcutsResponse>("/api/shortcuts"),
  });

  function clearForm() {
    setKeyword("");
    setLabel("");
    setHomeUrl("");
    setSearchExample("");
    setSearchWords("");
    setEditing(null);
  }

  function startEdit(shortcut: Shortcut) {
    setKeyword(shortcut.keyword);
    setLabel(shortcut.label);
    setHomeUrl(shortcut.home_url);
    // A saved template still has {words}, which Core keeps as it is.
    setSearchExample(shortcut.search_url ?? "");
    setSearchWords("");
    setEditing(shortcut.keyword);
    setError(null);
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    const fields = {
      label,
      home_url: homeUrl,
      search_example: searchExample.trim() || null,
      search_words: searchWords.trim() || null,
    };
    try {
      // Editing sends PUT without the keyword; Core takes it from the link.
      const response = await fetch(
        editing ? `/api/shortcuts/${editing}` : "/api/shortcuts",
        {
          method: editing ? "PUT" : "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(editing ? fields : { keyword, ...fields }),
        },
      );
      const data = await response.json();
      if (!response.ok) {
        // Core's own messages are strings; field errors come as a list.
        setError(
          typeof data.detail === "string" ? data.detail : "Check the fields.",
        );
        return;
      }
      clearForm();
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
      if (editing === name) clearForm();
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
            <ShortcutRow
              key={shortcut.keyword}
              shortcut={shortcut}
              buttonClass={BUTTON_CLASS}
              disabled={busy}
              onEdit={startEdit}
              onDelete={remove}
            />
          ))}
        </ul>
      )}

      <form onSubmit={save} className="mt-4 space-y-3">
        {editing && (
          <p className="text-sm font-medium">Editing {editing}</p>
        )}
        <label className="block text-sm">
          Keyword
          <input
            type="text"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            disabled={editing !== null}
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
          Example search link (optional)
          <input
            type="text"
            inputMode="url"
            value={searchExample}
            onChange={(event) => setSearchExample(event.target.value)}
            placeholder="https://site.com/search?q=naruto"
            autoComplete="off"
            aria-describedby="search-example-hint"
            className={INPUT_CLASS}
          />
        </label>
        <p id="search-example-hint" className="-mt-2 text-xs text-muted">
          Search for anything on the site, then paste the link from the address
          bar.
        </p>
        <label className="block text-sm">
          What you searched for (optional)
          <input
            type="text"
            value={searchWords}
            onChange={(event) => setSearchWords(event.target.value)}
            placeholder="naruto"
            autoComplete="off"
            aria-describedby="search-words-hint"
            className={INPUT_CLASS}
          />
        </label>
        <p id="search-words-hint" className="-mt-2 text-xs text-muted">
          Only needed if Venus can&apos;t find your search in the link.
        </p>
        <div className="flex gap-2">
          <button
            type="submit"
            disabled={
              busy || !keyword.trim() || !label.trim() || !homeUrl.trim()
            }
            className={BUTTON_CLASS}
          >
            {editing ? "Save" : "Add shortcut"}
          </button>
          {editing && (
            <button
              type="button"
              disabled={busy}
              onClick={clearForm}
              className={BUTTON_CLASS}
            >
              Cancel
            </button>
          )}
        </div>
      </form>

      {error && (
        <p role="alert" className="mt-2 text-sm text-danger">
          {error}
        </p>
      )}
    </section>
  );
}
