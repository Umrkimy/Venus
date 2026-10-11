"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Upload } from "lucide-react";
import { useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { useCharacterInfo } from "@/features/scene/use-character-info";

function megabytes(bytes: number): string {
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

// Your own .vrm: Core keeps it (private, backed up), every device shows it.
export default function CharacterModel() {
  const queryClient = useQueryClient();
  const info = useCharacterInfo();
  const fileRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

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
        fetch(`/api/character/model?name=${encodeURIComponent(file.name)}`, {
          method: "PUT",
          headers: { "Content-Type": "application/octet-stream" },
          body: file,
        }),
      "Couldn't upload that model.",
    );
  }

  function backToTemplate() {
    void change(
      () => fetch("/api/character/model", { method: "DELETE" }),
      "Couldn't go back to the template.",
    );
  }

  const own = info.data?.custom ? info.data : null;

  return (
    <div className="mt-4">
      <p className="text-sm">
        {info.isPending
          ? "Checking your model..."
          : own
            ? `Your model: ${own.name} (${megabytes(own.size)})`
            : "Template model (AvatarSample_A)"}
      </p>
      <div className="mt-2 flex flex-wrap gap-2">
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
        <Button type="button" variant="outline" size="sm" disabled={busy} onClick={() => fileRef.current?.click()}>
          <Upload />
          {busy ? "Saving..." : "Upload .vrm"}
        </Button>
        {own && (
          <Button type="button" variant="ghost" size="sm" disabled={busy} onClick={backToTemplate}>
            Use template
          </Button>
        )}
      </div>
      <p className="mt-2 text-sm text-muted-foreground">
        Get models from VRoid Hub. Check each creator&apos;s terms before using one.
      </p>
      {error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {error}
        </p>
      )}
    </div>
  );
}
