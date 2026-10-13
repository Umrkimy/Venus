import { Suspense } from "react";

import CalendarSettings from "@/features/calendar/calendar-settings";
import SettingsSection from "@/features/settings/settings-section";

export default function CalendarSettingsPage() {
  return (
    <SettingsSection
      title="Calendar"
      description="Connect Google and Outlook so Venus knows your classes and meetings. Read-only."
    >
      {/* It reads ?connected= or ?error= after signing in, which needs Suspense. */}
      <Suspense>
        <CalendarSettings />
      </Suspense>
    </SettingsSection>
  );
}
