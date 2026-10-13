import HomeAssistant from "@/features/home/home-assistant";
import HomeDevices from "@/features/home/home-devices";
import SettingsSection from "@/features/settings/settings-section";

export default function HomeSettingsPage() {
  return (
    <SettingsSection
      title="Home"
      description="Lights, plugs, your TV, air-con and other PCs Venus can control from the chat or by voice."
    >
      <HomeDevices />
      <div className="mt-8 border-t border-border pt-5">
        <p className="mb-4 text-sm font-semibold">Home Assistant</p>
        <HomeAssistant />
      </div>
    </SettingsSection>
  );
}
