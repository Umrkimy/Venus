import SettingsSection from "@/features/settings/settings-section";
import UsageSummary from "@/features/settings/usage-summary";

export default function UsageSettingsPage() {
  return (
    <SettingsSection
      title="Usage"
      description="OpenAI cost for chat and voice-to-text, per day."
    >
      <UsageSummary />
    </SettingsSection>
  );
}
