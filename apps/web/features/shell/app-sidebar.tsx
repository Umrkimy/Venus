"use client";

import { useQuery } from "@tanstack/react-query";
import { LogOut, Plus, Settings } from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
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

  const conversations = useQuery({
    queryKey: ["conversations"],
    queryFn: () => getJson<ConversationSummary[]>("/api/conversations"),
  });

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
              {conversations.data?.map((conversation) => {
                const href = `/chat/${conversation.id}`;
                return (
                  <SidebarMenuItem key={conversation.id}>
                    <SidebarMenuButton asChild isActive={pathname === href}>
                      <Link href={href}>
                        <span>{conversation.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
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
    </Sidebar>
  );
}
