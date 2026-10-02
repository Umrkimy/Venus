"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { FIELD_HOVER, LABEL_CLASS } from "@/features/settings/field-styles";
import { getJson } from "@/lib/get-json";

import ShortcutRow from "./shortcut-row";

export type Shortcut = {
  keyword: string;
  label: string;
  home_url: string;
  search_url: string | null;
};
type ShortcutsResponse = { shortcuts: Shortcut[] };

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
  // "Saved comix" / "Added comix" after a successful save.
  const [notice, setNotice] = useState<string | null>(null);

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
    setNotice(null);
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
    setNotice(null);
  }

  async function save(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setNotice(null);
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
      // Stay on the edited shortcut and show what Core really saved.
      if (editing) {
        setLabel(data.label);
        setHomeUrl(data.home_url);
        setSearchExample(data.search_url ?? "");
        setSearchWords("");
        setNotice(`Saved ${data.keyword}`);
      } else {
        // clearForm also clears the notice, so set it afterwards.
        clearForm();
        setNotice(`Added ${data.keyword}`);
      }
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
    <div>
      {shortcuts.isPending && (
        <div role="status">
          <span className="sr-only">Loading shortcuts</span>
          <div className="h-12 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
        </div>
      )}

      {shortcuts.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load shortcuts.
        </p>
      )}

      {shortcuts.isSuccess && shortcuts.data.shortcuts.length === 0 && (
        <p className="text-sm text-muted-foreground">No shortcuts yet.</p>
      )}

      {shortcuts.isSuccess && shortcuts.data.shortcuts.length > 0 && (
        <ul className="space-y-2">
          {shortcuts.data.shortcuts.map((shortcut) => (
            <ShortcutRow
              key={shortcut.keyword}
              shortcut={shortcut}
              editing={editing === shortcut.keyword}
              disabled={busy}
              onEdit={startEdit}
              onDelete={remove}
            />
          ))}
        </ul>
      )}

      <form onSubmit={save} className="mt-5 space-y-4 border-t border-border pt-5">
        <p className="text-sm font-semibold">
          {editing ? (
            <>
              Editing{" "}
              <span className="rounded bg-primary/10 px-1.5 py-0.5 font-mono text-primary">
                {editing}
              </span>
            </>
          ) : (
            "Add a shortcut"
          )}
        </p>
        <label className={LABEL_CLASS}>
          Keyword
          <Input
            type="text"
            value={keyword}
            onChange={(event) => setKeyword(event.target.value)}
            disabled={editing !== null}
            placeholder="comix"
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <label className={LABEL_CLASS}>
          Name
          <Input
            type="text"
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Comix"
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <label className={LABEL_CLASS}>
          Home link
          <Input
            type="text"
            inputMode="url"
            value={homeUrl}
            onChange={(event) => setHomeUrl(event.target.value)}
            placeholder="https://site.com"
            autoComplete="off"
            className={FIELD_HOVER}
          />
        </label>
        <label className={LABEL_CLASS}>
          Example search link (optional)
          <Input
            type="text"
            inputMode="url"
            value={searchExample}
            onChange={(event) => setSearchExample(event.target.value)}
            placeholder="https://site.com/search?q=naruto"
            autoComplete="off"
            aria-describedby="search-example-hint"
            className={FIELD_HOVER}
          />
        </label>
        <p id="search-example-hint" className="-mt-3 text-xs text-muted-foreground">
          Search for anything on the site, then paste the link from the address
          bar.
        </p>
        <label className={LABEL_CLASS}>
          What you searched for (optional)
          <Input
            type="text"
            value={searchWords}
            onChange={(event) => setSearchWords(event.target.value)}
            placeholder="naruto"
            autoComplete="off"
            aria-describedby="search-words-hint"
            className={FIELD_HOVER}
          />
        </label>
        <p id="search-words-hint" className="-mt-3 text-xs text-muted-foreground">
          Only needed if Venus can&apos;t find your search in the link.
        </p>
        <div className="flex gap-2">
          <Button
            type="submit"
            variant="outline"
            disabled={
              busy || !keyword.trim() || !label.trim() || !homeUrl.trim()
            }
          >
            {editing ? "Save" : "Add shortcut"}
          </Button>
          {editing && (
            <Button
              type="button"
              variant="ghost"
              disabled={busy}
              onClick={clearForm}
            >
              Cancel
            </Button>
          )}
        </div>
      </form>

      {notice && (
        <p role="status" className="mt-2 text-sm">
          {notice}
        </p>
      )}

      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
