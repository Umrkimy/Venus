"use client";

import { Archive, MoreHorizontal, Pencil, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
} from "@/components/ui/sidebar";
import ChatPanel from "@/features/chat/chat-panel";
import { useNewChat } from "@/features/chat/new-chat";
import DeleteProjectDialog from "@/features/projects/delete-project-dialog";
import ProjectNameDialog from "@/features/projects/project-name-dialog";
import {
  type Project,
  useProjectActions,
  useProjects,
} from "@/features/projects/use-projects";
import { useChatActions, useConversations } from "@/features/shell/chat-actions";
import ChatMenu from "@/features/shell/chat-menu";

// /project/<id>: the project's name, a chat box that starts chats inside it,
// and its chats until you send the first message.
export default function ProjectView({ projectId }: { projectId: string }) {
  const projects = useProjects();
  const { count } = useNewChat();

  if (projects.isPending) {
    return (
      <div role="status" className="mx-auto w-full max-w-2xl px-4">
        <span className="sr-only">Loading project</span>
        <div className="h-8 w-48 rounded-md bg-foreground/20 motion-safe:animate-pulse" />
      </div>
    );
  }

  const project = projects.data?.find((p) => p.id === projectId);
  if (!project) {
    return (
      <div role="alert" className="m-auto text-center">
        <p className="text-destructive">
          {projects.isError ? "Can't load projects." : "This project doesn't exist."}
        </p>
        <Button asChild variant="outline" className="mt-3">
          <Link href="/">Start a new chat</Link>
        </Button>
      </div>
    );
  }

  return (
    <>
      <ProjectHeader project={project} />
      {/* key: New chat or clicking the project again starts an empty card. */}
      <ChatPanel
        key={count}
        conversationId={null}
        initialMessages={[]}
        projectId={project.id}
        emptyState={<ProjectChats project={project} />}
      />
    </>
  );
}

function ProjectHeader({ project }: { project: Project }) {
  const router = useRouter();
  const actions = useProjectActions();
  const [renaming, setRenaming] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function rename(name: string) {
    setRenaming(false);
    await actions.rename(project.id, name);
  }

  // Archived projects leave the sidebar and can't be opened, so go home.
  async function archive() {
    if (await actions.setArchived(project.id, true)) router.push("/");
  }

  async function remove() {
    setDeleting(false);
    if (await actions.remove(project.id)) router.push("/");
  }

  return (
    <div className="mx-auto w-full max-w-2xl px-4 pb-3">
      <div className="flex items-center gap-2">
        <h1 className="min-w-0 truncate text-xl font-semibold tracking-tight">
          {project.name}
        </h1>
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon-sm" aria-label="Project actions">
              <MoreHorizontal />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuItem onSelect={() => setRenaming(true)}>
              <Pencil />
              Rename
            </DropdownMenuItem>
            <DropdownMenuItem onSelect={archive}>
              <Archive />
              Archive
            </DropdownMenuItem>
            <DropdownMenuItem
              variant="destructive"
              onSelect={() => setDeleting(true)}
            >
              <Trash2 />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      {actions.error && (
        <p role="alert" className="mt-1 text-sm text-destructive">
          {actions.error}
        </p>
      )}

      <ProjectNameDialog
        open={renaming}
        title="Rename project"
        submitLabel="Save"
        initialName={project.name}
        onCancel={() => setRenaming(false)}
        onSubmit={rename}
      />
      <DeleteProjectDialog
        project={deleting ? project : null}
        onCancel={() => setDeleting(false)}
        onConfirm={remove}
      />
    </div>
  );
}

function ProjectChats({ project }: { project: Project }) {
  const conversations = useConversations();
  const actions = useChatActions();
  const chats = conversations.data?.filter(
    (conversation) => conversation.project_id === project.id,
  );

  return (
    <div className="mx-auto mt-10 max-w-md">
      <p className="text-center text-2xl font-semibold tracking-tight text-balance">
        Start a chat in {project.name}
      </p>
      {chats && chats.length > 0 && (
        <div className="mt-8">
          <p className="px-2 text-xs font-medium text-muted-foreground">
            Chats in this project
          </p>
          <SidebarMenu className="mt-1">
            {chats.map((conversation) => (
              <SidebarMenuItem key={conversation.id}>
                <SidebarMenuButton asChild>
                  <Link href={`/chat/${conversation.id}`}>
                    <span>{conversation.title}</span>
                  </Link>
                </SidebarMenuButton>
                <ChatMenu conversation={conversation} actions={actions} />
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </div>
      )}
      {actions.error && (
        <p role="alert" className="mt-2 text-sm text-destructive">
          {actions.error}
        </p>
      )}
    </div>
  );
}
