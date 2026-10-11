"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useCharacterMoves } from "@/features/scene/use-character-info";
import type { MoveUse } from "@/features/scene/uploaded-moves";

const USES: { value: MoveUse; label: string }[] = [
  { value: "idle", label: "Idle (random)" },
  { value: "hello", label: "Hello (once)" },
  { value: "listening", label: "Listening" },
  { value: "thinking", label: "Thinking" },
  { value: "talking", label: "Talking" },
];

function kilobytes(bytes: number): string {
  return `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// Your own .vrma moves: Core keeps them (private, backed up). A mood with no
// move here uses Venus's coded moves.
export default function CharacterMoves() {
  const queryClient = useQueryClient();
  const moves = useCharacterMoves();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function change(requests: (() => Promise<Response>)[], failed: string) {
    setBusy(true);
    setError(null);
    try {
      for (const request of requests) {
        const response = await request();
        if (!response.ok) {
          const data = await response.json().catch(() => null);
          setError(typeof data?.detail === "string" ? data.detail : failed);
          break;
        }
      }
      // The scene sees the new list and loads the moves again.
      await queryClient.invalidateQueries({ queryKey: ["character", "animations"] });
    } catch {
      setError("Can't reach Venus Core. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  function upload(files: File[]) {
    void change(
      files.map(
        (file) => () =>
          fetch(`/api/character/animations?name=${encodeURIComponent(file.name)}`, {
            method: "POST",
            headers: { "Content-Type": "application/octet-stream" },
            body: file,
          }),
      ),
      "Couldn't upload that move.",
    );
  }

  function setUse(id: number, use: MoveUse) {
    void change(
      [
        () =>
          fetch(`/api/character/animations/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ use }),
          }),
      ],
      "Couldn't change that move.",
    );
  }

  function remove(id: number) {
    void change(
      [() => fetch(`/api/character/animations/${id}`, { method: "DELETE" })],
      "Couldn't delete that move.",
    );
  }

  const list = moves.data ?? [];

  return (
    <div className="mt-6">
      <p className="text-sm font-medium">Moves</p>
      {list.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">
          {moves.isPending ? "Checking your moves..." : "None yet: Venus uses her coded moves."}
        </p>
      ) : (
        <ul className="mt-2 space-y-2">
          {list.map((move) => (
            <li key={move.id} className="flex items-center gap-2">
              <span className="min-w-0 flex-1 truncate text-sm" title={move.name}>
                {move.name} <span className="text-muted-foreground">({kilobytes(move.size)})</span>
              </span>
              <Select
                value={move.use}
                disabled={busy}
                onValueChange={(use) => setUse(move.id, use as MoveUse)}
              >
                <SelectTrigger
                  aria-label={`When ${move.name} plays`}
                  className="w-36 font-normal data-[size=default]:h-9 hover:border-foreground/40"
                >
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {USES.map((use) => (
                    <SelectItem key={use.value} value={use.value}>
                      {use.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                disabled={busy}
                aria-label={`Delete ${move.name}`}
                onClick={() => remove(move.id)}
              >
                <Trash2 />
              </Button>
            </li>
          ))}
        </ul>
      )}
      <input
        ref={fileRef}
        type="file"
        accept=".vrma"
        multiple
        className="hidden"
        onChange={(event) => {
          const files = [...(event.target.files ?? [])];
          if (files.length) upload(files);
          event.target.value = ""; // Picking the same files again still uploads.
        }}
      />
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="mt-2"
        disabled={busy}
        onClick={() => fileRef.current?.click()}
      >
        <Upload />
        {busy ? "Saving..." : "Upload .vrma"}
      </Button>
      <p className="mt-2 text-sm text-muted-foreground">
        New moves start as idle; pick when each plays. Free moves: pixiv&apos;s VRMA motion pack on
        BOOTH. Kept by Venus Core on this PC, never in git.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
