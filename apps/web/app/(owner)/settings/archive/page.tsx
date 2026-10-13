import ArchiveTabs from "@/features/settings/archive-tabs";
import SettingsSection from "@/features/settings/settings-section";

export default function ArchiveSettingsPage() {
  return (
    <SettingsSection
      title="Archive"
      description="Archived chats and projects."
    >
      <ArchiveTabs />
    </SettingsSection>
  );
}
