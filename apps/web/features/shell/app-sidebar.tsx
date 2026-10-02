"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Archive,
  LogOut,
  MoreHorizontal,
  Plus,
  Settings,
  Trash2,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuAction,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarMenuSkeleton,
  SidebarRail,
} from "@/components/ui/sidebar";
import { useNewChat } from "@/features/chat/new-chat";
import { useChatActions } from "@/features/shell/chat-actions";
import DeleteChatDialog from "@/features/shell/delete-chat-dialog";
import { getJson } from "@/lib/get-json";
import { useNodes } from "@/lib/use-nodes";

export type ConversationSummary = { id: string; title: string; updated_at: string };

type AppSidebarProps = {
  username: string;
  onLogout: () => void;
};

export default function AppSidebar({ username, onLogout }: AppSidebarProps) {
  const pathname = usePathname();
  const { startNewChat } = useNewChat();
  const nodes = useNodes();
  const deviceId = nodes.data?.device_ids[0];
  const actions = useChatActions();
  const [deleting, setDeleting] = useState<ConversationSummary | null>(null);

  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => getJson<ConversationSummary[]>("/api/conversations"),
  });

  async function confirmDelete() {
    if (deleting === null) return;
    const id = deleting.id;
    setDeleting(null);
    await actions.deleteChat(id);
  }

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
        {actions.error && (
          <p role="alert" className="px-4 pt-2 text-sm text-destructive">
            {actions.error}
          </p>
        )}

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
            {conversations.data?.length === 0 && (
              <p className="px-2 text-sm text-muted-foreground">
                No chats yet. Say hi to Venus.
              </p>
            )}
            <SidebarMenu>
              {conversations.data?.map((conversation) => (
                <ChatRow
                  key={conversation.id}
                  conversation={conversation}
                  active={pathname === `/chat/${conversation.id}`}
                  onArchive={() => actions.setArchived(conversation.id, true)}
                  onDelete={() => setDeleting(conversation)}
                />
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      <SidebarFooter>
        <p className="flex items-center gap-2 px-2 text-sm text-muted-foreground">
          <span
            aria-hidden="true"
            className={`size-2 rounded-full ${deviceId ? "bg-primary" : "bg-muted-foreground/50"}`}
          />
          {deviceId ? `${deviceId} online` : "PC offline"}
        </p>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton asChild isActive={pathname === "/settings"}>
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

      <DeleteChatDialog
        title={deleting?.title ?? null}
        onCancel={() => setDeleting(null)}
        onConfirm={confirmDelete}
      />
    </Sidebar>
  );
}

type ChatRowProps = {
  conversation: ConversationSummary;
  active: boolean;
  onArchive: () => void;
  onDelete: () => void;
};

function ChatRow({
  conversation,
  active,
  onArchive,
  onDelete,
}: ChatRowProps) {
  return (
    <SidebarMenuItem>
      <SidebarMenuButton asChild isActive={active}>
        <Link href={`/chat/${conversation.id}`}>
          <span>{conversation.title}</span>
        </Link>
      </SidebarMenuButton>
      {/* modal={false}: a modal menu closing as the dialog opens can leave the page unclickable. */}
      <DropdownMenu modal={false}>
        <DropdownMenuTrigger asChild>
          <SidebarMenuAction showOnHover>
            <MoreHorizontal />
            <span className="sr-only">Chat actions</span>
          </SidebarMenuAction>
        </DropdownMenuTrigger>
        <DropdownMenuContent side="right" align="start">
          <DropdownMenuItem onSelect={onArchive}>
            <Archive />
            Archive
          </DropdownMenuItem>
          <DropdownMenuItem variant="destructive" onSelect={onDelete}>
            <Trash2 />
            Delete
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </SidebarMenuItem>
  );
}
