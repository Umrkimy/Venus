import ModeSwitch from "@/features/settings/mode-switch";
import SettingsSection from "@/features/settings/settings-section";
import ThemeSwitch from "@/features/settings/theme-switch";
import TimeSettings from "@/features/settings/time-settings";

export default function GeneralSettingsPage() {
  return (
    <>
      <SettingsSection
        title="Appearance"
        description="Light or dark, or match your PC."
      >
        <ThemeSwitch />
      </SettingsSection>
      <SettingsSection
        title="Command mode"
        description="Whether Venus asks before opening things on your PC."
      >
        <ModeSwitch />
      </SettingsSection>
      <SettingsSection
        title="Time and place"
        description="Your time zone and country, so Venus knows your time and date."
      >
        <TimeSettings />
      </SettingsSection>
    </>
  );
}
