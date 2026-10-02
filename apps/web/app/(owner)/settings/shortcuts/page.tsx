import SettingsSection from "@/features/settings/settings-section";
import Shortcuts from "@/features/shortcuts/shortcuts";

export default function ShortcutsSettingsPage() {
  return (
    <SettingsSection
      title="Shortcuts"
      description="Keywords that open or search a site, like “comix naruto”."
    >
      <Shortcuts />
    </SettingsSection>
  );
}
