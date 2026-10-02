"use client";

import { useQuery } from "@tanstack/react-query";
import { ArchiveRestore, Trash2 } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  type ConversationSummary,
  useChatActions,
} from "@/features/shell/chat-actions";
import DeleteChatDialog from "@/features/shell/delete-chat-dialog";
import { getJson } from "@/lib/get-json";

// Archived chats live here, out of the sidebar. Unarchive sends one back.
export default function ArchivedChats() {
  const actions = useChatActions();
  const [deleting, setDeleting] = useState<ConversationSummary | null>(null);

  const archived = useQuery({
    queryKey: ["conversations", "archived"],
    queryFn: () =>
      getJson<ConversationSummary[]>("/api/conversations?archived=true"),
  });

  async function confirmDelete() {
    if (deleting === null) return;
    const id = deleting.id;
    setDeleting(null);
    await actions.deleteChat(id);
  }

  return (
    <div>
      {archived.isPending && (
        <div role="status">
          <span className="sr-only">Loading archived chats</span>
          <div className="h-12 w-full rounded-md bg-foreground/20 motion-safe:animate-pulse" />
        </div>
      )}

      {archived.isError && (
        <p role="alert" className="text-sm text-destructive">
          Can&apos;t load archived chats.
        </p>
      )}

      {archived.isSuccess && archived.data.length === 0 && (
        <p className="text-sm text-muted-foreground">Nothing archived.</p>
      )}

      {archived.isSuccess && archived.data.length > 0 && (
        <ul className="space-y-2">
          {archived.data.map((conversation) => (
            <li
              key={conversation.id}
              className="group flex items-center justify-between gap-3 rounded-lg border border-border px-4 py-3 transition-colors hover:border-foreground/30 hover:bg-muted/60"
            >
              <p className="min-w-0 truncate">{conversation.title}</p>
              {/* Faded until the row is hovered or focused, always visible on touch. */}
              <div className="flex shrink-0 gap-1 transition-opacity md:opacity-60 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon-sm"
                      onClick={() => actions.setArchived(conversation.id, false)}
                      aria-label={`Unarchive ${conversation.title}`}
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
                      onClick={() => setDeleting(conversation)}
                      aria-label={`Delete ${conversation.title}`}
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

      <DeleteChatDialog
        title={deleting?.title ?? null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </div>
  );
}
