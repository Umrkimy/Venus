import { Suspense } from "react";

import CalendarSettings from "@/features/calendar/calendar-settings";
import IcsCalendars from "@/features/calendar/ics-calendars";
import SettingsSection from "@/features/settings/settings-section";

export default function CalendarSettingsPage() {
  return (
    <>
      <SettingsSection title="Google and Outlook" description="Read, add and change events.">
        {/* Reads ?connected= or ?error= after signing in, which needs Suspense. */}
        <Suspense>
          <CalendarSettings />
        </Suspense>
      </SettingsSection>
      <SettingsSection title="Timetables (.ics)" description="Read-only calendars from a link or a file, like a uni portal.">
        <IcsCalendars />
      </SettingsSection>
    </>
  );
}
