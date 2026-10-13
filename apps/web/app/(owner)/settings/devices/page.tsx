import DeviceList from "@/features/devices/device-list";
import SessionList from "@/features/devices/session-list";
import SettingsSection from "@/features/settings/settings-section";

export default function DevicesSettingsPage() {
  return (
    <div className="space-y-4">
      <SettingsSection
        title="PCs"
        description="PCs running Venus, each with its own token."
      >
        <DeviceList />
      </SettingsSection>
      <SettingsSection
        title="Signed-in browsers"
        description="Browsers signed in to Venus."
      >
        <SessionList />
      </SettingsSection>
    </div>
  );
}
