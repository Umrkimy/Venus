import MemoryList from "@/features/memories/memory-list";
import SettingsSection from "@/features/settings/settings-section";

export default function MemorySettingsPage() {
  return (
    <SettingsSection
      title="Memory"
      description="Facts Venus keeps about you. The 50 newest go into every chat."
    >
      <MemoryList />
    </SettingsSection>
  );
}
