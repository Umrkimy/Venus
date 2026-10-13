# Developing

For changing the code: Core and the web page run from source with
auto-reload, Postgres stays in Docker. You also need
[Node.js 22+](https://nodejs.org/). One-time setup after the normal setup:

```powershell
# Windows
cd apps/core;  py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ../node;  .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd ../web;   npm ci
```

```bash
# Linux
cd apps/core && python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m alembic upgrade head
cd ../node && .venv/bin/pip install -r requirements-dev.txt
cd ../web && npm ci
```

Then `start-venus.cmd` (Windows, opens Core, Node, web and the listener as
Windows Terminal tabs) or `./start-venus.sh` (Linux, all in one terminal,
Ctrl+C stops everything). Quit the tray app first, it can't run next to the
dev Node. After pulling new migrations run `alembic upgrade head` in
`apps/core` (server mode does that by itself).

## Tests

```bash
cd apps/core && .venv/bin/python -m pytest      # Core (SQLite in memory)
cd apps/node && .venv/bin/python -m pytest      # Node
apps/node/.venv/bin/python -m pytest packages/venus-protocol/tests
cd apps/web && npx tsc --noEmit && npm run lint # Web
```

(On Windows it's `.venv\Scripts\python.exe` instead of `.venv/bin/python`.)

CI runs all of that on Windows and Linux, Core again on real Postgres, builds
the Docker images and tests a backup restore. To run Core's tests on Postgres
locally, make a scratch database whose name ends in `_test` (the tests wipe
its tables) and set `VENUS_CORE_TEST_DATABASE_URL` to it.

## Portfolio demo build

A static copy of the web page with a pretend Core that runs in the browser
(no server, no AI, no keys, nothing touches a PC). It's for my portfolio
site, not something you need to run Venus.

```bash
cd apps/web
npm run build:demo     # plain files in apps/web/out
```

Build it on Linux or in CI: a Windows build names some prefetch files wrong
(page switches get a bit slower). The pretend Core is
`apps/web/features/demo/fake-core.ts`, her lines are in
`features/demo/script.ts`.

[Back to the README](../README.md)
