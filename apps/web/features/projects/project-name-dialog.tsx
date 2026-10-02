"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";

type ProjectNameDialogProps = {
  open: boolean;
  title: string;
  submitLabel: string;
  initialName?: string;
  onCancel: () => void;
  onSubmit: (name: string) => void;
};

// One box for both "New project" and "Rename project".
export default function ProjectNameDialog({
  open,
  title,
  submitLabel,
  initialName = "",
  onCancel,
  onSubmit,
}: ProjectNameDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onCancel();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        {/* Mounted only while open, so it starts from initialName each time. */}
        {open && (
          <NameForm
            initialName={initialName}
            submitLabel={submitLabel}
            onCancel={onCancel}
            onSubmit={onSubmit}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

type NameFormProps = Omit<ProjectNameDialogProps, "open" | "title">;

function NameForm({ initialName = "", submitLabel, onCancel, onSubmit }: NameFormProps) {
  const [name, setName] = useState(initialName);

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSubmit(name.trim());
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <label className="flex flex-col gap-1.5 text-sm font-medium">
        Name
        <Input
          value={name}
          onChange={(event) => setName(event.target.value)}
          maxLength={60}
          placeholder="Java assignment"
          autoComplete="off"
          autoFocus
        />
      </label>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={name.trim() === ""}>
          {submitLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}
