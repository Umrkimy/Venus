import PersonalityList from "@/features/personalities/personality-list";
import SettingsSection from "@/features/settings/settings-section";

export default function PersonalitySettingsPage() {
  return (
    <SettingsSection
      title="Personality"
      description="Who Venus is when she talks to you. Switching applies from the next message in every chat."
    >
      <PersonalityList />
    </SettingsSection>
  );
}
