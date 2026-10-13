import HomeDevices from "@/features/home/home-devices";
import SettingsSection from "@/features/settings/settings-section";

export default function HomeSettingsPage() {
  return (
    <SettingsSection
      title="Home"
      description="Lights, plugs, your TV and other PCs Venus can control from the chat or by voice."
    >
      <HomeDevices />
    </SettingsSection>
  );
}
