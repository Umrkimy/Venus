"use client";

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

import type { Memory } from "./use-memories";

type DeleteMemoryDialogProps = {
  // The memory waiting for an answer, or null when the dialog is closed.
  memory: Memory | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function DeleteMemoryDialog({
  memory,
  onCancel,
  onConfirm,
}: DeleteMemoryDialogProps) {
  return (
    <AlertDialog
      open={memory !== null}
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Forget this?</AlertDialogTitle>
          <AlertDialogDescription className="break-words">
            &ldquo;{memory?.text}&rdquo; will be deleted. This can&apos;t be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={onConfirm}>
            Delete
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
