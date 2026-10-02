"use client";

import { Folder, LogOut, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useState } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupAction,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useNewChat } from "@/features/chat/new-chat";
import ProjectNameDialog from "@/features/projects/project-name-dialog";
import {
  useProjectActions,
  useProjects,
} from "@/features/projects/use-projects";
import { useChatActions, useConversations } from "@/features/shell/chat-actions";
import ChatMenu from "@/features/shell/chat-menu";

type AppSidebarProps = {
  username: string;
  onLogout: () => void;
};

export default function AppSidebar({ username, onLogout }: AppSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { startNewChat } = useNewChat();
  const actions = useChatActions();
  const projectActions = useProjectActions();
  const [creating, setCreating] = useState(false);

  const projects = useProjects();
  const conversations = useConversations();
  // Chats in a project live on the project's page, not here.
  const looseChats = conversations.data?.filter(
    (conversation) => conversation.project_id === null,
  );

  async function createProject(name: string) {
    setCreating(false);
    const project = await projectActions.create(name);
    if (project) router.push(`/project/${project.id}`);
  }

  const error = actions.error ?? projectActions.error;

  return (
    <Sidebar>
      <SidebarHeader>
        <p className="px-2 pt-1 text-lg font-semibold tracking-tight">Venus</p>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild>
              <Link href="/" onClick={startNewChat}>
                <Plus />
                <span>New chat</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarContent>
        {error && (
          <p role="alert" className="px-4 pt-2 text-sm text-destructive">
            {error}
          </p>
        )}

        <SidebarGroup>
          <SidebarGroupLabel>Projects</SidebarGroupLabel>
          <SidebarGroupAction title="New project" onClick={() => setCreating(true)}>
            <Plus />
            <span className="sr-only">New project</span>
          </SidebarGroupAction>
          <SidebarGroupContent>
            {projects.isError && (
              <p role="alert" className="px-2 text-sm text-destructive">
                Can&apos;t load projects.
              </p>
            )}
            {projects.data?.length === 0 && (
              <p className="px-2 text-sm text-muted-foreground">
                Group chats for an assignment or a bit of code.
              </p>
            )}
            <SidebarMenu>
              {projects.data?.map((project) => {
                const href = `/project/${project.id}`;
                return (
                  <SidebarMenuItem key={project.id}>
                    <SidebarMenuButton asChild isActive={pathname === href}>
                      {/* startNewChat: clicking the project again empties its chat card. */}
                      <Link href={href} onClick={startNewChat}>
                        <Folder />
                        <span>{project.name}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>

        <SidebarGroup>
          <SidebarGroupLabel>Chats</SidebarGroupLabel>
          <SidebarGroupContent>
            {conversations.isPending && (
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuSkeleton />
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuSkeleton />
                </SidebarMenuItem>
              </SidebarMenu>
            )}
            {conversations.isError && (
              <p role="alert" className="px-2 text-sm text-destructive">
                Can&apos;t load chats.
              </p>
            )}
            {looseChats?.length === 0 && (
              <p className="px-2 text-sm text-muted-foreground">
                No chats yet. Say hi to Venus.
              </p>
            )}
            <SidebarMenu>
              {looseChats?.map((conversation) => {
                const href = `/chat/${conversation.id}`;
                return (
                  <SidebarMenuItem key={conversation.id}>
                    <SidebarMenuButton asChild isActive={pathname === href}>
                      <Link href={href}>
                        <span>{conversation.title}</span>
                      </Link>
                    </SidebarMenuButton>
                    <ChatMenu conversation={conversation} actions={actions} />
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={pathname.startsWith("/settings")}>
              <Link href="/settings">
                <Settings />
                <span>Settings</span>
              </Link>
            </SidebarMenuButton>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton onClick={onLogout}>
              <LogOut />
              <span>Log out {username}</span>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      <SidebarRail />

      <ProjectNameDialog
        open={creating}
        title="New project"
        submitLabel="Create"
        onCancel={() => setCreating(false)}
        onSubmit={createProject}
      />
    </Sidebar>
  );
}
