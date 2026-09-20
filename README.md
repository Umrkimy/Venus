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
send typed fake commands to a connected Node, and the Node returns typed fake
results. The connection path never launches Spotify; the separate `dev_run`
developer command is the only path that asks Windows to launch it.

The explicit local developer command can request Windows to open Spotify using
the Node's private `spotify:` target. It bypasses future confirmation policy
and does not prove Spotify is healthy after Windows accepts the launch request.
No other Windows application is allowlisted yet. There is no web UI,
production owner authentication/enrollment flow, paid AI provider, or internet
exposure.

## Requirements

- Windows
- Python 3.11+

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
VENUS_NODE_SPOTIFY_TARGET=spotify:
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

## Run the authenticated fake Node connection

Start Core first, then run this in a second PowerShell window:

```powershell
Set-Location apps/node
.\.venv\Scripts\python.exe -m venus_node.dev_connect
```

The Node prints `Core confirmed Node: ...` after the authenticated hello.

With Core and Node running, a third PowerShell window can request a fake
command. Replace the placeholder with the value in `apps/core/.env`:

```powershell
$headers = @{ Authorization = "Bearer your-development-owner-token" }
Invoke-RestMethod -Method Post -Headers $headers `
  http://127.0.0.1:8000/nodes/your-device-id/commands/fake
```

This exercises typed transport and fake SQLite command records. It does not
launch Spotify.

## Run the local Spotify developer command

Then run:

```powershell
Set-Location apps/node
.\.venv\Scripts\python.exe -m venus_node.dev_run
```

This intentionally asks Windows to open Spotify. It writes local command
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

## Safety boundary

Core may request a fake allowlisted action only after a development-owner token
check. The Windows Node owns the private Windows-specific application mapping
and independently validates each command. The current local Spotify developer
command reports that Windows accepted the launch request; it does not claim
Spotify playback or app health.
