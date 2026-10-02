"use client";

import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { SidebarInset, SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { NewChatProvider } from "@/features/chat/new-chat";
import OwnerStatus from "@/features/owner/owner-status";
import AppSidebar from "@/features/shell/app-sidebar";
import SceneBackground from "@/features/shell/scene-background";
import { useOwner } from "@/lib/use-owner";

export default function AppShell({ children }: { children: ReactNode }) {
  const { owner, logout } = useOwner();
  const signedIn = owner.status === "signed-in";
  // The scene belongs to the chat; settings get a plain solid page.
  const showScene = !usePathname().startsWith("/settings");

  return (
    <NewChatProvider>
      <SidebarProvider>
        {signedIn && <AppSidebar username={owner.username} onLogout={logout} />}
        <SidebarInset
          className={`relative h-svh overflow-hidden ${showScene ? "bg-transparent" : "bg-background"}`}
        >
          {showScene && <SceneBackground />}
          <header className="relative z-10 flex h-12 shrink-0 items-center px-3">
            {signedIn && <SidebarTrigger />}
          </header>
          <div className="relative z-10 flex min-h-0 flex-1 flex-col">
            <div className="px-4">
              <OwnerStatus owner={owner} />
            </div>
            {signedIn && children}
          </div>
        </SidebarInset>
      </SidebarProvider>
    </NewChatProvider>
  );
}
