"use client";

import { ArchiveRestore, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import DeleteProjectDialog from "@/features/projects/delete-project-dialog";
import {
  type Project,
  useArchivedProjects,
  useProjectActions,
} from "@/features/projects/use-projects";

// Archived projects hide with their chats. Unarchive brings both back.
export default function ArchivedProjects() {
  const actions = useProjectActions();
  const archived = useArchivedProjects();
  const [deleting, setDeleting] = useState<Project | null>(null);

  async function confirmDelete() {
    if (deleting === null) return;
    const id = deleting.id;
    setDeleting(null);
    await actions.remove(id);
  }

  return (
    <div>
      {archived.isPending && (
        <div role="status">
          <span className="sr-only">Loading archived projects</span>
          <div className="h-12 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
        </div>
      )}

      {archived.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load archived projects.
        </p>
      )}

      {archived.isSuccess && archived.data.length === 0 && (
        <p className="text-sm text-muted-foreground">No archived projects.</p>
      )}

      {archived.isSuccess && archived.data.length > 0 && (
        <ul className="space-y-2">
          {archived.data.map((project) => (
            <li
              key={project.id}
              className="group flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3 transition-colors hover:border-foreground/30 hover:bg-muted/60"
            >
              <div className="min-w-0">
                <p className="truncate">{project.name}</p>
                <p className="text-xs text-muted-foreground">
                  {project.chat_count} {project.chat_count === 1 ? "chat" : "chats"}
                </p>
              </div>
              {/* Faded until the row is hovered or focused, always visible on touch. */}
              <div className="flex shrink-0 gap-1 transition-opacity md:opacity-60 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => actions.setArchived(project.id, false)}
                      aria-label={`Unarchive ${project.name}`}
                      className="hover:text-primary"
                    >
                      <ArchiveRestore />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Unarchive</TooltipContent>
                </Tooltip>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => setDeleting(project)}
                      aria-label={`Delete ${project.name}`}
                      className="hover:bg-destructive/10 hover:text-destructive"
                    >
                      <Trash2 />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Delete</TooltipContent>
                </Tooltip>
              </div>
            </li>
          ))}
        </ul>
      )}

      {actions.error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {actions.error}
        </p>
      )}

      <DeleteProjectDialog
        project={deleting}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
