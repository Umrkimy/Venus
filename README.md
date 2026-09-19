# Venus

Venus is a personal AI platform designed around a portable Core, a native
Windows Node, and a future web control center.

## Current scope

This is an early, fake-only learning build. The repository currently includes:

- a FastAPI Core with `GET /health` and deterministic `POST /chat` endpoints;
- a shared Python command contract for one allowlisted application: Spotify;
- a fake Windows Node executor that validates command IDs, expiry, and target
  device IDs; and
- local SQLite command records that prevent duplicate fake actions, including
  after a Node restart.

The Node does **not** launch Spotify or any other Windows application yet.
There is no web UI, remote transport, authentication/enrollment flow, paid AI
provider, or internet exposure yet.

## Requirements

- Windows
- Python 3.11+

## Local setup

Create one virtual environment for Core and one for Node. Run these commands
from the repository root in PowerShell:

```powershell
py -3.11 -m venv apps/core/.venv
py -3.11 -m venv apps/node/.venv

.\apps\core\.venv\Scripts\python.exe -m pip install -r apps/core/requirements.txt
.\apps\core\.venv\Scripts\python.exe -m pip install -r apps/core/requirements-dev.txt
.\apps\node\.venv\Scripts\python.exe -m pip install -r apps/node/requirements.txt
.\apps\node\.venv\Scripts\python.exe -m pip install -r apps/node/requirements-dev.txt
```

Both application requirement files install the local `venus-protocol` package
in editable mode.

## Run Core

```powershell
Set-Location apps/core
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000/docs` to try the fake Core endpoints.

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
each command. Current execution is deliberately fake while the command
lifecycle and failure behavior are tested.
