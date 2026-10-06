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
| `apps/core/.env` | Node and owner tokens, database URL, encryption key, fallback AI/voice keys |
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
- One shared Node token today; per-device tokens are planned.
