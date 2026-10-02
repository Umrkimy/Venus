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

import type { Project } from "@/features/projects/use-projects";

type DeleteProjectDialogProps = {
  // The project waiting for an answer, or null when the dialog is closed.
  project: Project | null;
  onCancel: () => void;
  onConfirm: () => void;
};

// "and its 3 chats", "and its 1 chat", or nothing for an empty project.
function chatsPart(count: number) {
  if (count === 0) return "";
  return ` and its ${count} ${count === 1 ? "chat" : "chats"}`;
}

export default function DeleteProjectDialog({
  project,
  onCancel,
  onConfirm,
}: DeleteProjectDialogProps) {
  return (
    <AlertDialog
      open={project !== null}
      onOpenChange={(open) => {
        if (!open) onCancel();
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>
            Delete &ldquo;{project?.name}&rdquo;{chatsPart(project?.chat_count ?? 0)}?
          </AlertDialogTitle>
          <AlertDialogDescription>
            This can&apos;t be undone.
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
