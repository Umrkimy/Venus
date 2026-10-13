#!/usr/bin/env bash
# Load a Venus database backup (a .dump file from the backup service).
# Linux version of restore-db.ps1.
#
#   ./scripts/restore-db.sh backups/daily/venus-2026-10-06.dump
#       Replaces the live "venus" database. Saves the current one first
#       (pre-restore-<time>.dump next to the backup) and stops Core while
#       restoring, then starts it again.
#
#   ./scripts/restore-db.sh <dump> venus_restore_test
#       Restores into a throwaway database instead, to check that a backup
#       works without touching the real data. Remove it afterwards with
#       docker compose exec postgres dropdb -U venus venus_restore_test
#
# In dev mode, stop start-venus.sh (Ctrl+C) before restoring "venus".
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }
compose() { docker compose --project-directory "$root" "$@"; }

[[ $# -ge 1 ]] || fail "Usage: ./scripts/restore-db.sh <backup.dump> [database]"
file="$(realpath "$1")"
target="${2:-venus}"
[[ -f "$file" ]] || fail "No such file: $1"
[[ "$target" =~ ^[a-z_][a-z0-9_]*$ ]] || fail "The database must be a plain name (a-z, 0-9, _)."

if [[ "$target" == "venus" && "${FORCE:-}" != "1" ]]; then
    echo "This replaces the live Venus database with $file"
    read -r -p "Type RESTORE to continue: " answer
    [[ "$answer" == "RESTORE" ]] || { echo "Cancelled."; exit 0; }
fi

echo "Copying the backup into the Postgres container..."
compose cp "$file" postgres:/tmp/restore.dump

core_was_running=false
if [[ "$target" == "venus" ]]; then
    safety="$(dirname "$file")/pre-restore-$(date +%Y-%m-%d_%H%M%S).dump"
    echo "Saving the current database to $safety ..."
    compose exec -T postgres pg_dump -U venus -d venus -Fc -f /tmp/pre-restore.dump
    compose cp postgres:/tmp/pre-restore.dump "$safety"

    # Core holds open connections, which would block dropping the database.
    if compose --profile server ps --status running --services | grep -qx core; then
        core_was_running=true
        echo "Stopping Core..."
        compose --profile server stop core
    fi
fi

restart_core() {
    if $core_was_running; then
        echo "Starting Core again..."
        compose --profile server up -d --wait core
    fi
}
trap restart_core EXIT

echo "Restoring into database '$target'..."
compose exec -T postgres dropdb -U venus --if-exists --force "$target"
compose exec -T postgres createdb -U venus "$target"
compose exec -T postgres pg_restore -U venus -d "$target" --no-owner --exit-on-error /tmp/restore.dump
compose exec -T postgres rm -f /tmp/restore.dump /tmp/pre-restore.dump

echo "Restored $file into '$target'."
