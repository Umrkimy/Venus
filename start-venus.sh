#!/usr/bin/env bash
# Start Venus on Linux.
#
#   ./start-venus.sh --use
#       Everyday server mode, lighter on RAM. Postgres, Core and the built
#       web app run in Docker (`docker compose --profile server`), restart by
#       themselves and come back after a reboot (Docker starts at boot).
#       The tray app (connection, "Hey Venus", orb, tray icon) runs in the
#       background. Code changes: run this again (it rebuilds).
#
#   ./start-venus.sh
#       Development: Postgres in Docker, then Core, Node, the web page and
#       the "Hey Venus" listener in this terminal with auto-reload, their
#       output mixed together. Ctrl+C stops them all (Postgres keeps running
#       until `docker compose stop postgres`). Needs apps/core/.venv and
#       `npm install` in apps/web (README "Developing").
#
# Both modes use ports 9000 and 3000: this script stops the other mode first.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
node_dir="$root/apps/node"
node_python="$node_dir/.venv/bin/python"

fail() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }
port_in_use() { (exec 3<>"/dev/tcp/127.0.0.1/$1") 2>/dev/null; }
running() { pgrep -f "$1" >/dev/null 2>&1; }

[[ -f "$root/apps/core/.env" && -x "$node_python" ]] || fail "Venus is not set up yet. Run ./setup-venus.sh first."
docker info >/dev/null 2>&1 ||
    fail "Docker isn't running. Start it with: sudo systemctl enable --now docker"

compose() { docker compose --project-directory "$root" "$@"; }

if [[ "${1:-}" == "--use" ]]; then
    echo "Starting Venus server (Docker)..."
    # --build picks up code changes; --wait returns once all healthchecks pass.
    compose --profile server up -d --build --wait ||
        fail "Server mode did not start. Check 'docker compose --profile server logs'."
    if running "venus.pyw"; then
        echo "Venus tray app is already running."
    else
        # --hidden: messages go to apps/node/data/venus-node.log, not this terminal.
        (cd "$node_dir" && mkdir -p data && nohup "$node_python" venus.pyw --hidden >data/startup.log 2>&1 &)
    fi
    echo "Venus is running. Open http://localhost:3000"
    exit 0
fi

[[ -x "$root/apps/core/.venv/bin/python" ]] ||
    fail "Dev mode needs Core's own Python: cd apps/core && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt -r requirements-dev.txt"
[[ -d "$root/apps/web/node_modules" ]] || fail "Dev mode needs the web app's packages: cd apps/web && npm install"

# Dev mode uses the same ports as server mode: stop its containers first.
compose --profile server stop core web >/dev/null 2>&1 || true

echo "Starting Postgres and backups..."
compose up -d --wait postgres backup || fail "Postgres did not start. Check 'docker compose logs postgres'."

# Every part runs in the background of this terminal; Ctrl+C ends them all.
trap 'trap - INT TERM EXIT; echo; echo "Stopping Venus..."; kill 0' INT TERM EXIT

start() {
    local name="$1" folder="$2"
    shift 2
    # Each line gets the part's name in front, so mixed output stays readable.
    (cd "$folder" && "$@" 2>&1 | sed -u "s/^/[$name] /") &
}

if port_in_use 9000; then
    echo "Core is already running on port 9000."
else
    start core "$root/apps/core" .venv/bin/python -m uvicorn main:app --port 9000 --reload
fi

# The Node keeps retrying until Core is up, so it can start right away.
if running "venus_node.dev_connect"; then
    echo "Node is already running."
else
    start node "$node_dir" "$node_python" -m venus_node.dev_connect
fi

if port_in_use 3000; then
    echo "Web is already running on port 3000."
else
    start web "$root/apps/web" npm run dev
fi

# "Hey Venus": only talks to Core after a wake, so it can start right away.
if running "venus_node.cli.listen"; then
    echo "Hey Venus listener is already running."
else
    start listen "$node_dir" "$node_python" -m venus_node.cli.listen
fi

echo "Venus is starting. Open http://localhost:3000 in a few seconds. Ctrl+C stops it."
wait
