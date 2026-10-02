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

import type { Personality } from "./use-personalities";

type DeletePersonalityDialogProps = {
  // The personality waiting for an answer, or null when the dialog is closed.
  personality: Personality | null;
  onCancel: () => void;
  onConfirm: () => void;
};

export default function DeletePersonalityDialog({
  personality,
  onCancel,
  onConfirm,
}: DeletePersonalityDialogProps) {
  return (
    <AlertDialog
      open={personality !== null}
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete &ldquo;{personality?.name}&rdquo;?</AlertDialogTitle>
          <AlertDialogDescription>This can&apos;t be undone.</AlertDialogDescription>
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
