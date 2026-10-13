# Calendar

Venus has her own calendar, and can also show your Google Calendar,
Outlook (Microsoft 365) and timetable (.ics) calendars. She knows your next
7 days, so you can ask "what's on tomorrow" or "do I have anything Friday",
the first chat of the day starts with a short summary, and the PC part pops
up a reminder about 10 minutes before each event.

## The Calendar page

**Calendar** in the sidebar shows everything in one place: month, week, day
or a list. Each kind has its own colour (Venus red, Google blue, Outlook
teal, timetables purple).

- **Add**: click a day (month view) or drag over the times (week or day
  view), or **New event**. Pick which calendar it goes to: Venus's own
  (works without any sign-in), or Google or Outlook if connected.
- **Change**: click an event to edit or delete it, or drag it to another
  time and drag its bottom edge to make it longer.
- **By chat**: "add gym tomorrow at 6" or "put my exam on 2 November".
  Luna adds it to the Venus calendar and shows a calendar card.

Timetables (.ics) are read-only: change them in your uni portal. Google
calendars you can only view (like a holiday calendar) are read-only too.

**Already connected Google or Outlook before?** The first version only asked
to read. To add or change events there, click Disconnect and Connect again
in Settings, Calendar, so Google or Microsoft can ask you for the new
permission.

## Connecting Google and Outlook

Because Venus is self-hosted, you sign in through **your own** small app
at Google and Microsoft (free, a few minutes each). Do this on the PC with
Venus open at `http://localhost:3000`, because that's the address the sign-in
sends you back to. Settings, Calendar shows the exact redirect address
to paste.

**Google**

1. [Google Cloud Console](https://console.cloud.google.com/): make a project,
   then APIs & Services, Library, enable **Google Calendar API**.
2. OAuth consent screen: External, fill in the app name and your email,
   add yourself as a test user, then **Publish app** ("In production").
   While it's in "Testing", Google signs you out of it every 7 days.
   You'll see an "unverified app" warning when you connect; that's fine
   for your own app (Advanced, continue).
3. Credentials, Create credentials, OAuth client ID, type **Web
   application**, and add the redirect address from Settings, Calendar.
4. Copy the client ID and secret into Settings, Calendar, Save, then
   **Connect Google**.

**Outlook / Microsoft 365**

1. [Entra admin center](https://entra.microsoft.com/), App registrations,
   New registration. Account types: "Accounts in any organizational
   directory and personal Microsoft accounts". Redirect URI: platform
   **Web**, the address from Settings, Calendar.
2. Certificates & secrets, New client secret: copy the **Value** (it's
   only shown once).
3. Paste the Application (client) ID and the secret in Settings,
   Calendar, Save, **Connect Outlook**.

A school or work Microsoft account might say it needs admin approval.
That's your uni blocking outside apps, and only their IT can allow it. A
personal Outlook.com account always works.

The client secrets and sign-ins are stored encrypted. Remove in Settings,
Calendar forgets them; you can also remove Venus's access in your Google
or Microsoft account settings.

## Timetables and other calendars (.ics)

Many uni portals and apps can export a calendar as an **.ics** file (the
standard calendar format), even when they don't sync to Outlook or Google.
Venus reads those too, next to Google and Outlook.

In Settings, Calendar, under "Timetables and other calendars", give it a
name (like "Uni timetable") and either:

- **a link**, if the portal has a "subscribe" or "calendar feed" link
  (`https://...` or `webcal://...`). Venus downloads it again every few
  minutes while you use it, so timetable changes show up by themselves. The
  link is stored encrypted, because these links often contain a private key.
- **the .ics file**, if the portal only lets you download one. Venus keeps a
  copy. When the timetable changes, remove it and upload the new file.

It tells you how many events it found in the next 4 weeks. Repeating
classes ("every Monday 9:00") are understood. Times without a time zone in
the file are taken as your time zone from Settings, General. You can add as
many as you like (timetable, exams, a club).

[Back to the README](../README.md)
