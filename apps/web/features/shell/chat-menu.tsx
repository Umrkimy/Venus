"use client";

import {
  Archive,
  FolderInput,
  FolderMinus,
  MoreHorizontal,
  Trash2,
} from "lucide-react";
import { useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SidebarMenuAction } from "@/components/ui/sidebar";
import { useProjects } from "@/features/projects/use-projects";
import {
  type ConversationSummary,
  type useChatActions,
} from "@/features/shell/chat-actions";
import DeleteChatDialog from "@/features/shell/delete-chat-dialog";

type ChatMenuProps = {
  conversation: ConversationSummary;
  // Passed in, so the list that shows the menu also shows its errors.
  actions: ReturnType<typeof useChatActions>;
};

// The ⋯ menu on a chat row: move, archive, delete.
export default function ChatMenu({ conversation, actions }: ChatMenuProps) {
  const projects = useProjects();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const otherProjects =
    projects.data?.filter((project) => project.id !== conversation.project_id) ??
    [];

  return (
    <>
      {/* modal={false}: a modal menu closing as the dialog opens can leave the page unclickable. */}
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <SidebarMenuAction showOnHover>
            <MoreHorizontal />
            <span className="sr-only">Chat actions</span>
          </SidebarMenuAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="right" align="start">
          {otherProjects.length > 0 && (
            <DropdownMenuSub>
              <DropdownMenuSubTrigger>
                <FolderInput />
                Move to project
              </DropdownMenuSubTrigger>
              <DropdownMenuSubContent>
                {otherProjects.map((project) => (
                  <DropdownMenuItem
                    key={project.id}
                    onSelect={() => actions.moveToProject(conversation.id, project.id)}
                  >
                    {project.name}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          )}
          {conversation.project_id !== null && (
            <DropdownMenuItem
              onSelect={() => actions.moveToProject(conversation.id, null)}
            >
              <FolderMinus />
              Remove from project
            </DropdownMenuItem>
          )}
          {(otherProjects.length > 0 || conversation.project_id !== null) && (
            <DropdownMenuSeparator />
          )}
          <DropdownMenuItem
            onSelect={() => actions.setArchived(conversation.id, true)}
          >
            <Archive />
            Archive
          </DropdownMenuItem>
          <DropdownMenuItem
            variant="destructive"
            onSelect={() => setConfirmDelete(true)}
          >
            <Trash2 />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <DeleteChatDialog
        title={confirmDelete ? conversation.title : null}
        onCancel={() => setConfirmDelete(false)}
        onConfirm={() => {
          setConfirmDelete(false);
          actions.deleteChat(conversation.id);
        }}
      />
    </>
  );
}
