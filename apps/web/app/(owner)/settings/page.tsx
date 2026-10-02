"use client";

import ArchivedChats from "@/features/settings/archived-chats";
import LlmSettings from "@/features/settings/llm-settings";
import ModeSwitch from "@/features/settings/mode-switch";
import SettingsSection from "@/features/settings/settings-section";
import ThemeSwitch from "@/features/settings/theme-switch";
import Shortcuts from "@/features/shortcuts/shortcuts";

// The shell checks who is signed in and draws the sidebar around this.
export default function SettingsPage() {
  return (
    <div className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-2xl space-y-6 px-4 pb-16">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Settings</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            How Venus thinks, how much it asks, the sites it knows, and chats you put away.
          </p>
        </div>
        <SettingsSection
          title="AI model"
          description="The brain Venus uses for anything that isn't a direct command."
        >
          <LlmSettings />
        </SettingsSection>
        <SettingsSection
          title="Command mode"
          description="Whether Venus asks before opening things on your PC."
        >
          <ModeSwitch />
        </SettingsSection>
        <SettingsSection
          title="Appearance"
          description="Light or dark, or match your PC."
        >
          <ThemeSwitch />
        </SettingsSection>
        <SettingsSection
          title="Shortcuts"
          description="Keywords that open or search a site, like “comix naruto”."
        >
          <Shortcuts />
        </SettingsSection>
        <SettingsSection
          title="Archived chats"
          description="Chats you put away. Unarchive one to bring it back to the sidebar."
        >
          <ArchivedChats />
        </SettingsSection>
      </div>
    </div>
  );
}
