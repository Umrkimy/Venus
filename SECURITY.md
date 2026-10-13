# Security

Venus can open apps and links on your PC, so I take bugs that let someone
else control it seriously.

## Reporting a problem

Please don't open a public issue for a security bug. Use GitHub's private
report instead: the **Security** tab of this repo, then **Report a
vulnerability**. Tell me what you found, how to reproduce it, and what
someone could do with it. I'll answer as soon as I can.

## What counts

- Getting into Venus without the password, or keeping access after logout
  or after a device is revoked.
- Making a Node run anything other than an app from the menu, an
  `http`/`https` link or a folder inside the projects folder.
- Reading someone's saved API keys, chats or memories without logging in.
- Anything that lets a web page or another device reach Core directly.

## Not in scope

Venus is self-hosted. If you put Core or Postgres on the public internet
yourself (instead of `127.0.0.1` + Tailscale), or share your `.env` files,
that's on your setup, not a bug in Venus.

## How it's protected

- Core, the web page and Postgres only listen on `127.0.0.1`. Other devices
  only get in through Tailscale.
- Passwords are hashed (Argon2). Login tries are rate limited.
- Session cookies are `HttpOnly` and `SameSite=Lax`, and `Secure` over HTTPS.
- Core refuses changes sent by another website's page (it checks the
  browser's `Sec-Fetch-Site` header), so a random site can't press buttons
  in your Venus for you.
- API keys, Tuya keys and calendar sign-ins you save in Settings are
  encrypted (`VENUS_CORE_SECRET_KEY`) and never sent back to the page.
  Calendar access is read-only and uses PKCE plus a one-time state, so a
  sign-in can't be started by another site.
- Every PC has its own token, stored only as a hash, and can be revoked.
- The Node checks every command again on its own: only apps from your menu,
  only `http`/`https` links, only folders inside your projects folder. No
  shell commands, ever.
- Core refuses to start with the example tokens from `.env.example`.
- The web page sends security headers (no framing, no sniffing, mic only for
  this site).

More on tokens and signed-in browsers: [guide/remote-access.md](guide/remote-access.md#devices-and-logins).
