"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ArchivedChats from "@/features/settings/archived-chats";
import ArchivedProjects from "@/features/settings/archived-projects";

// One list at a time, so a long archive of chats doesn't bury the projects.
export default function ArchiveTabs() {
  return (
    <Tabs defaultValue="chats">
      <TabsList>
        <TabsTrigger value="chats">Chats</TabsTrigger>
        <TabsTrigger value="projects">Projects</TabsTrigger>
      </TabsList>
      <TabsContent value="chats" className="mt-3">
        <ArchivedChats />
      </TabsContent>
      <TabsContent value="projects" className="mt-3">
        <ArchivedProjects />
      </TabsContent>
    </Tabs>
  );
}
