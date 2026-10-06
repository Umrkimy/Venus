# Venus

Venus is a personal AI platform designed around a portable Core, a native
Windows Node, and a future web control center.

## Current scope

This is an early local-only learning build. The repository currently includes:

- a FastAPI Core with `GET /health` and deterministic `POST /chat` endpoints;
- a shared Python command contract for one allowlisted application: Spotify;
- a Windows Node executor that validates command IDs, expiry, and target
  device IDs before dispatch; and
- local SQLite command records that prevent duplicate actions, including after
  a Node restart.

Core and Node also have an authenticated local WebSocket connection. Core can
propose an Open Spotify command for a Node; after the owner approves it, Core
sends it to the connected Node and the Node returns a typed result. The Node
launches Spotify only when `VENUS_NODE_REAL_ACTIONS=true` is set in
`apps/node/.env` (default `false`, which records a fake result).

The explicit local developer command can request Windows to open Spotify using
the Node's private `spotify:` target. It bypasses future confirmation policy
and does not prove Spotify is healthy after Windows accepts the launch request.
No other Windows application is allowlisted yet. A minimal Next.js web UI in
`apps/web` can sign the owner in and out through Core. There is no paid AI
provider or internet exposure.

## Requirements

- Windows
- Python 3.11+
- Node.js 22+ (for the web UI)

## Local setup

Create one virtual environment for Core and one for Node. Run these commands
from the repository root in PowerShell:

```powershell
Push-Location apps/core
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location

Push-Location apps/node
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

Both Core and Node install the local `venus-protocol` package in editable mode.
It defines the shared WebSocket message contracts.

## Local private configuration

Copy the placeholder files, then replace every placeholder with your own local
values. Do not commit either `.env` file.

```powershell
Copy-Item apps/core/.env.example apps/core/.env
Copy-Item apps/node/.env.example apps/node/.env
```

`apps/core/.env` needs two different secrets:

```text
VENUS_CORE_DEV_NODE_TOKEN=your-shared-development-node-token
VENUS_CORE_DEV_OWNER_TOKEN=your-development-owner-token
```

`apps/node/.env` needs the same Node token, plus its local identity and Core
WebSocket URL:

```text
VENUS_NODE_DEVICE_ID=your-device-id
VENUS_NODE_CORE_DEV_TOKEN=your-shared-development-node-token
VENUS_NODE_CORE_URL=ws://127.0.0.1:8000/nodes/connect
```

The Node token proves a Node may connect. The owner token protects the
development-only fake HTTP dispatch route; never reuse the Node token for it.

## Run Core

```powershell
Set-Location apps/core
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the fake Core endpoints.

## Run the web UI

Start Core first. Then install and start the web app:

```powershell
Set-Location apps/web
npm install
npm run dev
```

Open `http://localhost:3000/login`. The web app forwards `/api/*` to Core, so
the browser only talks to one origin and the session cookie works without
CORS. Core defaults to `http://127.0.0.1:8000`; to point elsewhere, copy
`apps/web/.env.example` to `apps/web/.env.local` and set `CORE_URL`.

## Run the authenticated fake Node connection

Start Core first, then run this in a second PowerShell window:

```powershell
Set-Location apps/node
.\.venv\Scripts\python.exe -m venus_node.dev_connect
```

The Node prints `Core confirmed Node: ...` after the authenticated hello.

With Core and Node running, use the web UI, or a third PowerShell window, to
propose a command (today only `spotify` is allowed). Replace the placeholder with the value in
`apps/core/.env`:

```powershell
$headers = @{ Authorization = "Bearer your-development-owner-token" }
Invoke-RestMethod -Method Post -Headers $headers `
  -ContentType "application/json" -Body '{"application_id": "spotify"}' `
  http://127.0.0.1:8000/nodes/your-device-id/commands
```

This creates a proposal that waits for approval. Approve it with
`POST /commands/{command_id}/approval` and the body `{"approved": true}`.
With real actions off, the Node records a fake result and does not launch
Spotify.

## Run the local app developer command

Then run, with an AppID from `Get-StartApps`:

```powershell
Set-Location apps/node
.\.venv\Scripts\python.exe -m venus_node.dev_run <AppID>
```

This intentionally asks Windows to open that app. It writes local command
history to the Git-ignored `apps/node/data/node.db` and prints the command
result. Use it only as a local developer check; it bypasses future Core policy,
confirmation, and network authentication.

## Tests

Run each suite from the indicated directory:

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
```

## Database backups

Docker Compose runs a `backup` service next to Postgres (needs Docker
Desktop, or Docker Engine 25+). It saves one backup when it starts and then
one per day, keeping the newest 7 daily and 4 weekly files:

```text
<backup folder>/daily/venus-YYYY-MM-DD.dump
<backup folder>/weekly/venus-YYYY-Www.dump
```

The backup folder is `./backups` in the repository unless you set
`VENUS_BACKUP_DIR` in the root `.env` (see `.env.example`). Prefer a folder
on another drive. Start it with Postgres:

```powershell
docker compose up -d --wait postgres backup
```

`docker compose ps` shows the service as unhealthy when no backup is newer
than 26 hours.

To restore, run the script from the repository root (PowerShell; on Linux or
macOS install `pwsh`). Try a backup safely on a throwaway database first:

```powershell
.\scripts\restore-db.ps1 -File backups\daily\venus-2026-10-06.dump -Target venus_restore_test
```

Without `-Target` it replaces the live `venus` database. It asks you to type
`RESTORE`, saves the current database as `pre-restore-<time>.dump` next to
the backup file, and stops Core while restoring (close Core yourself if you
run it outside Docker).

## Safety boundary

Core may request a fake allowlisted action only after a development-owner token
check. The Windows Node owns the private Windows-specific application mapping
and independently validates each command. The current local app developer
command reports that Windows accepted the launch request; it does not claim
the app is healthy.
