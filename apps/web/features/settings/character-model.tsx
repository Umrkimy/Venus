"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Trash2, Upload } from "lucide-react";
import { useRef, useState } from "react";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { type CharacterModelInfo, useCharacterModels } from "@/features/scene/use-character-info";

function megabytes(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// One row: the template or an uploaded model, with "Use this" when it isn't in use.
function ModelRow({
  name,
  detail,
  active,
  busy,
  onUse,
  onDelete,
}: {
  name: string;
  detail: string;
  active: boolean;
  busy: boolean;
  onUse: () => void;
  onDelete?: () => void;
}) {
  return (
    <li className="flex items-center gap-2">
      <span className="min-w-0 flex-1 truncate text-sm" title={name}>
        {name} <span className="text-muted-foreground">({detail})</span>
      </span>
      {active ? (
        <Badge>In use</Badge>
      ) : (
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={onUse}>
          Use this
        </Button>
      )}
      {/* The one in use can't be deleted, so its button isn't offered. */}
      {onDelete && !active && (
        <Button
          type="button"
          variant="ghost"
          size="icon-sm"
          disabled={busy}
          aria-label={`Delete ${name}`}
          onClick={onDelete}
          className="text-muted-foreground hover:text-destructive"
        >
          <Trash2 />
        </Button>
      )}
    </li>
  );
}

// Your own .vrm models: every device shows the one in use. Switching keeps the others.
export default function CharacterModel() {
  const queryClient = useQueryClient();
  const models = useCharacterModels();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<CharacterModelInfo | null>(null);

  async function change(request: () => Promise<Response>, failed: string) {
    setBusy(true);
    setError(null);
    try {
      const response = await request();
      if (!response.ok) {
        const data = await response.json().catch(() => null);
        setError(typeof data?.detail === "string" ? data.detail : failed);
        return;
      }
      // The scene sees the new answer and loads her again.
      await queryClient.invalidateQueries({ queryKey: ["character"] });
    } catch {
      setError("Can't reach Venus. Is it running?");
    } finally {
      setBusy(false);
    }
  }

  function upload(file: File) {
    void change(
      () =>
        fetch(`/api/character/models?name=${encodeURIComponent(file.name)}`, {
          method: "POST",
          headers: { "Content-Type": "application/octet-stream" },
          body: file,
        }),
      "Couldn't upload that model.",
    );
  }

  function use(id: number | null) {
    void change(
      () =>
        fetch("/api/character/active", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ id }),
        }),
      "Couldn't switch models.",
    );
  }

  function confirmDelete() {
    const model = deleting;
    setDeleting(null);
    if (model) {
      void change(
        () => fetch(`/api/character/models/${model.id}`, { method: "DELETE" }),
        "Couldn't delete that model.",
      );
    }
  }

  const list = models.data ?? [];
  const templateInUse = !list.some((model) => model.active);

  return (
    <div className="mt-4">
      <p className="text-sm font-medium">Model</p>
      {models.isPending ? (
        <p className="mt-1 text-sm text-muted-foreground">Checking your models...</p>
      ) : (
        <ul className="mt-2 space-y-2">
          <ModelRow
            name="AvatarSample_A"
            detail="template"
            active={templateInUse}
            busy={busy}
            onUse={() => use(null)}
          />
          {list.map((model) => (
            <ModelRow
              key={model.id}
              name={model.name}
              detail={megabytes(model.size)}
              active={model.active}
              busy={busy}
              onUse={() => use(model.id)}
              onDelete={() => setDeleting(model)}
            />
          ))}
        </ul>
      )}
      <input
        ref={fileRef}
        type="file"
        accept=".vrm"
        className="hidden"
        onChange={(event) => {
          const file = event.target.files?.[0];
          if (file) upload(file);
          event.target.value = ""; // Picking the same file again still uploads.
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
        {busy ? "Saving..." : "Upload .vrm"}
      </Button>
      <p className="mt-2 text-sm text-muted-foreground">
        Get models from VRoid Hub. Check each creator&apos;s terms before using one.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
      <AlertDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete &ldquo;{deleting?.name}&rdquo;?</AlertDialogTitle>
            <AlertDialogDescription>
              This can&apos;t be undone. You&apos;d have to upload the file again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={confirmDelete}>
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
