# Email

Venus can show your inbox, sum it up, and write replies for you. She never
sends anything herself: you read the draft, change what you like, and press
**Send** (and confirm).

## Add a mailbox

Settings, Email, Add an account: your address, the name people should see,
and an **app password**. An app password is a separate password made just
for Venus. Your normal password doesn't work there, and you can delete an
app password any time without changing your real one.

- **Gmail**: [Google Account](https://myaccount.google.com/), Security, turn
  on 2-Step Verification, then search for **App passwords** and make one
  called "Venus".
- **iCloud**: [account.apple.com](https://account.apple.com/), Sign-In and
  Security, App-Specific Passwords.
- **Yahoo**: Account Info, Account security, Generate app password.
- **Others** (Fastmail, your own domain...): use their app password, and tick
  "Set the mail servers myself" for the IMAP (reading) and SMTP (sending)
  servers from their help pages.
- **Uni Microsoft 365 and Outlook.com**: Microsoft switched off app
  passwords for mail, so these need the Microsoft sign-in, which is the next
  update.

Venus signs in once to check the password before saving it. It's stored
encrypted and never shown again.

## The Email page

**Email** in the sidebar:

- The inbox, newest first, unread in bold. Opening a message marks it read,
  like any mail app. Mail is shown as plain text: no images or tracking
  pixels load, and no scripts run.
- **Sum up inbox**: Luna's short overview of what matters (uni, deadlines,
  people waiting for you) and what's just promotions.
- **Sum up** on a message: who wants what, any deadline, what you should do.
- **Reply with Luna**: pick a tone (professional, friendly, short) and
  optionally say what the reply should say ("yes, by Friday"). Luna writes
  it, signed with your name. If she doesn't know something, she leaves a
  [placeholder] instead of making it up.
- **Write**: a new email. "Ask Luna to write it" fills in the text from a
  sentence like "ask Dr. Aina for a 2-day extension".

Summaries and drafts send that email's text to your AI model (OpenAI), and
they show up in Settings, Usage. Luna gets no tools while reading mail, so
an email that says "ignore your instructions" can't make Venus do anything:
at worst it changes the words of a draft you read before sending.

[Back to the README](../README.md)
