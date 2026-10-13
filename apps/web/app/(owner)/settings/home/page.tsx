import HomeAssistant from "@/features/home/home-assistant";
import HomeDevices from "@/features/home/home-devices";
import SettingsSection from "@/features/settings/settings-section";

export default function HomeSettingsPage() {
  return (
    <>
      <SettingsSection title="Home Assistant" description="Lights, switches, TVs, air-con and scenes from your Home Assistant.">
        <HomeAssistant />
      </SettingsSection>
      <SettingsSection title="Devices" description="What Venus can control by chat or voice.">
        <HomeDevices />
      </SettingsSection>
    </>
  );
}
