# Venus

Venus is a personal assistant for your Windows PC. You type or say
"Hey Venus", and she opens apps, sites and code projects, chats with you
through an AI model (Luna), remembers what you tell her and answers out loud.
Everything runs on your own PC: nothing is hosted for you, and you bring your
own API keys.

Parts:

- **Core** (`apps/core`): FastAPI server, the brain. Saves chats, memories and
  settings in PostgreSQL, talks to the AI and voice providers, sends commands
  to your PC.
- **Web** (`apps/web`): Next.js page at `http://localhost:3000`: chat,
  settings, shortcuts.
- **Node** (`apps/node`): the PC part. A tray app that runs commands on
  Windows, listens for "Hey Venus" and shows the orb.
- **Protocol** (`packages/venus-protocol`): message formats shared by Core and
  Node.

## Requirements

- Windows 10 or 11
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (runs
  Postgres, Core and the web page)
- [Python 3.11+](https://www.python.org/downloads/) (runs the PC part; tick
  "Add python.exe to PATH")
- Optional keys: [OpenAI](https://platform.openai.com/) for chat,
  [Fish Audio](https://fish.audio/) for her voice. Without them Venus still
  opens apps and sites from typed commands.

## Quick start

```powershell
git clone https://github.com/Umrkimy/Venus.git
cd Venus
.\setup-venus.cmd
```

Or double-click `setup-venus.cmd`. It:

1. checks Docker and Python,
2. writes `.env`, `apps/core/.env` and `apps/node/.env` with fresh random
   secrets (files that already exist are kept, so it is safe to run again),
3. installs the PC part into `apps/node/.venv`,
4. downloads the "Hey Venus" speech model (Vosk, about 40 MB),
5. builds and starts Venus in Docker (the first build takes a few minutes),
6. asks for your username and password.

Then open `http://localhost:3000`, sign in, and add your keys under
**Settings** (they are saved encrypted in the database).

## Everyday use

Double-click `start-venus-use.cmd`. Postgres, Core and the web page run in
Docker, restart by themselves after a crash, and come back after a reboot
once Docker Desktop starts (Docker Desktop settings: "Start Docker Desktop
when you sign in"). The tray icon is the PC part: right-click it for Open
Venus, Mute mic, Stop talking, **Start with Windows** and Quit.

Say "Hey Venus", then talk. "Thank you Venus" or "bye" ends the conversation;
"stop Venus" interrupts her.

After pulling new code, run `start-venus-use.cmd` again: it rebuilds the
containers.

## Settings files

`setup-venus.ps1` writes these; the `.env.example` next to each explains
every value. Never commit a `.env` file.

| File | Holds |
| --- | --- |
| `.env` | Postgres password, backup folder (Docker Compose) |
| `apps/core/.env` | Node token, database URL, encryption key, fallback AI/voice keys |
| `apps/node/.env` | This PC's name, the Node token (same as Core's), wake phrases, projects folder, mic |

Common changes in `apps/node/.env`: `VENUS_NODE_PROJECTS_ROOT` (folder with
your code projects, for "open project X"), `VENUS_NODE_WAKE_PHRASES`,
`VENUS_NODE_MIC`. Restart the tray app afterwards (tray menu Quit, then
`start-venus-use.cmd`).

## Development mode

For changing the code: Core and the web page run from source with
auto-reload, Postgres stays in Docker. Also needs
[Node.js 22+](https://nodejs.org/). One-time setup after `setup-venus.cmd`:

```powershell
Push-Location apps/core
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location

Push-Location apps/node
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location

Push-Location apps/web
npm ci
Pop-Location
```

Then double-click `start-venus.cmd`. It stops the server-mode Core and web
containers (same ports 9000 and 3000) and opens Core, Node, web and the
"Hey Venus" listener as tabs of one Windows Terminal window. Quit the tray
app first; it and the dev Node tabs cannot run at the same time. Run
`.\.venv\Scripts\python.exe -m alembic upgrade head` in `apps/core` after
pulling new database migrations (server mode does this by itself).

## Database backups

Docker Compose runs a `backup` service next to Postgres. It saves one backup
when it starts and then one per day, keeping the newest 7 daily and 4 weekly
files:

```text
<backup folder>/daily/venus-YYYY-MM-DD.dump
<backup folder>/weekly/venus-YYYY-Www.dump
```

The backup folder is `./backups` in the repository unless you set
`VENUS_BACKUP_DIR` in the root `.env` (see `.env.example`). Prefer a folder
on another drive. `docker compose ps` shows the service as unhealthy when no
backup is newer than 26 hours.

To restore, run the script from the repository root (PowerShell; on Linux or
macOS install `pwsh`). Try a backup safely on a throwaway database first:

```powershell
.\scripts\restore-db.ps1 -File backups\daily\venus-2026-10-06.dump -Target venus_restore_test
```

Without `-Target` it replaces the live `venus` database. It asks you to type
`RESTORE`, saves the current database as `pre-restore-<time>.dump` next to
the backup file, and stops Core while restoring (close Core yourself in
development mode).

## Use Venus on your phone

Venus can be opened from your phone (or a laptop) through
[Tailscale](https://tailscale.com), a free private network between your own
devices. Only devices signed in to your Tailscale account can reach it;
nothing is opened to the public internet. The address uses HTTPS, so the
browser microphone works there too.

1. Install Tailscale on the PC and the phone and sign in to the same account.
2. In the Tailscale admin console, on the DNS page, turn on MagicDNS and
   HTTPS Certificates.
3. With Venus running, run from the repository root:

```powershell
.\scripts\phone-access.ps1
```

It prints an address like `https://my-pc.tailnet-name.ts.net`. Open it on the
phone with the Tailscale app connected and log in as usual. Sharing stays on
after a reboot; `.\scripts\phone-access.ps1 -Off` stops it.

### Your own domain (optional)

Instead of the `ts.net` address you can use a domain you own, for example
`https://venus.example.com`. It stays private: the domain points to the PC's
Tailscale address, which only your own devices can reach.
[Caddy](https://caddyserver.com) answers on that address (about 45 MB of RAM)
and gets a free Let's Encrypt certificate by proving domain ownership through
your DNS. The steps below assume the domain's DNS is at Cloudflare.

1. Set up Tailscale as above. Find the PC's Tailscale address with
   `tailscale ip -4` (it starts with `100.`).
2. In Cloudflare, add an `A` record (for example `venus`) pointing to that
   address, with the proxy turned off ("DNS only", grey cloud).
3. In Cloudflare, create an API token with the "Edit zone DNS" template,
   limited to that one domain.
4. In the `.env` in the repository root, set `VENUS_DOMAIN` (the full name,
   for example `venus.example.com`) and `CLOUDFLARE_API_TOKEN`.
5. Run:

```powershell
.\scripts\domain-access.ps1
```

It downloads Caddy with the Cloudflare module into `tools\caddy` (it asks
first), stops the `ts.net` share (Caddy takes port 443 instead) and restarts
the Venus tray app. From then on the tray app runs Caddy whenever it runs,
also after a reboot. Caddy's messages go to `apps
ode\data\caddy.log`.

To stop using the domain, empty `VENUS_DOMAIN`, quit Venus from the tray and
start it again, then run `.\scripts\phone-access.ps1` for the `ts.net`
address.

## Devices (PC tokens)

Each PC running the Venus Node has its own token. Settings, Devices lists
them with when each was last seen, and Revoke cuts one off at once without
touching the others. Revoked PCs can then be deleted from the list.

- The token that `setup-venus.ps1` writes (`VENUS_CORE_DEV_NODE_TOKEN`) shows
  up as "Main PC" the first time the Node connects. The main PC can't be
  revoked from the web, so a stolen phone login can't cut it off. To replace
  its token, change it in both `apps/core/.env` and `apps/node/.env` and
  restart; the old main token then stops working.
- A token works for one PC only: it is locked to the first `VENUS_NODE_DEVICE_ID`
  that uses it, so a copied token can't pretend to be another PC.
- Add device gives a new token once. Put it in that PC's `apps/node/.env` as
  `VENUS_NODE_CORE_DEV_TOKEN`. Core keeps only a hash of it.
- A revoked token stays revoked. To use that PC again, add it as a new device.

The same page lists every signed-in browser (for example "iPhone · Safari")
with when it was last active. Sign out ends one login at once; "Sign out all
other browsers" is for a lost phone. Logins end by themselves after 7 days.

Core only listens on this PC for now, so a second PC can't reach it yet; that
comes with remote Nodes later.

## Troubleshooting

- **Port 5432, 9000 or 3000 in use**: another Postgres, or dev mode and server
  mode at once. Stop the other one. After a reboot Windows can reserve 5432;
  in an admin terminal run `net stop winnat` then `net start winnat`.
- **"password authentication failed"**: the Postgres data was created with an
  older password than the one in `.env`. Put the old password back, or (this
  deletes all Venus data) `docker compose down -v` and run setup again.
- **Tray app does nothing**: see `apps/node/data/venus-node.log`.
- **Mic in the browser**: only works on `localhost` or HTTPS.
- Never use Docker Desktop's "Reset to factory defaults": it deletes the
  database volume. Restore from a backup if it happens.

## Tests

```powershell
# Core
Set-Location apps/core
.\.venv\Scripts\python.exe -m pytest

# Node
Set-Location ../node
.\.venv\Scripts\python.exe -m pytest

# Shared protocol, from the repository root
Set-Location ../..
.\apps\node\.venv\Scripts\python.exe -m pytest packages/venus-protocol/tests

# Web
Set-Location apps/web
npx tsc --noEmit
npm run lint
```

## Safety

- Core, web and Postgres listen on `127.0.0.1` only; nothing is reachable from
  other devices.
- PC actions need your approval in the chat unless you switch Settings to Full
  mode. The Node checks every command again before running it.
- API keys saved in Settings are encrypted with `VENUS_CORE_SECRET_KEY`; the
  page never shows them back.
- Each PC has its own Node token, stored only as a hash; revoke one in
  Settings, Devices.
