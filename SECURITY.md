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

See the "Security" part of the [README](README.md#security).
