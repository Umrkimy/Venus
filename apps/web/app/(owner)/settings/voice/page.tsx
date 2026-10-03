import ReadingForm from "@/features/settings/reading-form";
import SettingsSection from "@/features/settings/settings-section";
import VoiceSettings from "@/features/settings/voice-settings";

export default function VoiceSettingsPage() {
  return (
    <>
      <SettingsSection
        title="Luna's voice"
        description="Fish Audio speaks Luna's replies. The key is stored encrypted in Core."
      >
        <VoiceSettings />
      </SettingsSection>
      <SettingsSection
        title="Voice & text"
        description="How Luna's replies come out in chat. Saved in this browser."
      >
        <ReadingForm />
      </SettingsSection>
    </>
  );
}
