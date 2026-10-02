import ArchiveTabs from "@/features/settings/archive-tabs";
import SettingsSection from "@/features/settings/settings-section";

export default function ArchiveSettingsPage() {
  return (
    <SettingsSection
      title="Archive"
      description="Chats and projects you put away. Unarchive one to bring it back to the sidebar."
    >
      <ArchiveTabs />
    </SettingsSection>
  );
}
