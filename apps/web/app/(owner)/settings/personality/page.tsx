import PersonalityList from "@/features/personalities/personality-list";
import SettingsSection from "@/features/settings/settings-section";

export default function PersonalitySettingsPage() {
  return (
    <SettingsSection
      title="Personality"
      description="How Venus talks. Applies from the next message."
    >
      <PersonalityList />
    </SettingsSection>
  );
}
