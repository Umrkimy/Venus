import ReadingForm from "@/features/settings/reading-form";
import SettingsSection from "@/features/settings/settings-section";

export default function VoiceSettingsPage() {
  return (
    <SettingsSection
      title="Voice & text"
      description="How Luna's replies come out in chat. Saved in this browser."
    >
      <ReadingForm />
    </SettingsSection>
  );
}
