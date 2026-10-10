import ListeningSettings from "@/features/settings/listening-settings";
import ReadingForm from "@/features/settings/reading-form";
import SettingsSection from "@/features/settings/settings-section";
import VoiceSettings from "@/features/settings/voice-settings";

export default function VoiceSettingsPage() {
  return (
    <>
      <SettingsSection
        title="Venus's voice"
        description="Fish Audio speaks Venus's replies. The key is stored encrypted in Core."
      >
        <VoiceSettings />
      </SettingsSection>
      <SettingsSection
        title="Listening"
        description="When Venus sends what you said (web and PC) and which mic the PC hears you with. Saved in Core."
      >
        <ListeningSettings />
      </SettingsSection>
      <SettingsSection
        title="Voice & text"
        description="How Venus's replies come out in chat. Saved in this browser."
      >
        <ReadingForm />
      </SettingsSection>
    </>
  );
}
