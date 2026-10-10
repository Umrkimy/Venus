import SettingsSection from "@/features/settings/settings-section";
import UsageSummary from "@/features/settings/usage-summary";

export default function UsageSettingsPage() {
  return (
    <SettingsSection
      title="Usage"
      description="What chat and voice-to-text used on OpenAI, counted by Core from each reply. Days follow your time zone."
    >
      <UsageSummary />
    </SettingsSection>
  );
}
