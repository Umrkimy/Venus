import LlmSettings from "@/features/settings/llm-settings";
import SettingsSection from "@/features/settings/settings-section";

export default function AiSettingsPage() {
  return (
    <SettingsSection
      title="AI model"
      description="The model for chat and anything that isn't a direct command."
    >
      <LlmSettings />
    </SettingsSection>
  );
}
