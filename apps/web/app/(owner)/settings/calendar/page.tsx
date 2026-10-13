import { Suspense } from "react";

import CalendarSettings from "@/features/calendar/calendar-settings";
import IcsCalendars from "@/features/calendar/ics-calendars";
import SettingsSection from "@/features/settings/settings-section";

export default function CalendarSettingsPage() {
  return (
    <SettingsSection
      title="Calendar"
      description="Connect Google, Outlook or a timetable file so Venus knows your classes and meetings. Add and change events on the Calendar page."
    >
      {/* It reads ?connected= or ?error= after signing in, which needs Suspense. */}
      <Suspense>
        <CalendarSettings />
      </Suspense>
      <IcsCalendars />
    </SettingsSection>
  );
}
