# Calendar

Venus can read your Google Calendar and Outlook (Microsoft 365) calendars.
She knows your next 7 days, so you can ask "what's on tomorrow" or "do I
have anything Friday", the first chat of the day starts with a short
summary, and the PC part pops up a reminder about 10 minutes before each
event. It's read-only: Venus can't add or change events.

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

[Back to the README](../README.md)
