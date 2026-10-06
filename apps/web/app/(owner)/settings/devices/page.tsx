import DeviceList from "@/features/devices/device-list";
import SessionList from "@/features/devices/session-list";
import SettingsSection from "@/features/settings/settings-section";

export default function DevicesSettingsPage() {
  return (
    <div className="space-y-4">
      <SettingsSection
        title="PCs"
        description="PCs that run Venus. Each has its own token, so you can cut one off without touching the others."
      >
        <DeviceList />
      </SettingsSection>
      <SettingsSection
        title="Signed-in browsers"
        description="Every phone, laptop or PC browser logged in to Venus. Logins end by themselves after 7 days."
      >
        <SessionList />
      </SettingsSection>
    </div>
  );
}
