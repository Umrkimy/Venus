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

The explicit local developer command can request Windows to open Spotify using
the Node's private `spotify:` target. It is not connected to Core, does not
implement owner confirmation or remote authentication, and does not prove that
Spotify is healthy after Windows accepts the launch request. No other Windows
application is allowlisted yet. There is no web UI, remote transport,
authentication/enrollment flow, paid AI provider, or internet exposure.

## Requirements

- Windows
- Python 3.11+

## Local setup

Create one virtual environment for Core and one for Node. Run these commands
from the repository root in PowerShell:

```powershell
py -3.11 -m venv apps/core/.venv
.\apps\core\.venv\Scripts\python.exe -m pip install -r apps/core/requirements.txt
.\apps\core\.venv\Scripts\python.exe -m pip install -r apps/core/requirements-dev.txt

Push-Location apps/node
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Pop-Location
```

The Node installs the local `venus-protocol` package in editable mode. Core
does not depend on that package yet.

## Run Core

```powershell
Set-Location apps/core
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the fake Core endpoints.

## Run the local Spotify developer command

Create `apps/node/.env` locally (it is Git-ignored):

```text
VENUS_NODE_DEVICE_ID=laptop-1
VENUS_NODE_SPOTIFY_TARGET=spotify:
```

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

Core may eventually request an allowlisted action, but the Windows Node owns
the private Windows-specific application mapping and independently validates
each command. The current local Spotify developer command reports that Windows
accepted the launch request; it does not claim Spotify playback or app health.
