# Load a Venus database backup (a .dump file from the backup service).
#
#   .\scripts\restore-db.ps1 -File E:\VenusBackups\daily\venus-2026-10-06.dump
#       Replaces the live "venus" database. Saves the current one first
#       (pre-restore-<time>.dump next to the backup) and stops Core while
#       restoring, then starts it again.
#
#   .\scripts\restore-db.ps1 -File <dump> -Target venus_restore_test
#       Restores into a throwaway database instead, to check that a backup
#       works without touching the real data. Remove it afterwards with
#       docker compose exec postgres dropdb -U venus venus_restore_test
#
# In dev mode, close the Core window before restoring "venus".
param(
    [Parameter(Mandatory = $true)][string]$File,
    [string]$Target = "venus",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

function Invoke-Compose {
    docker compose --project-directory $root @args
    if ($LASTEXITCODE -ne 0) { throw "docker compose $args failed." }
}

$File = (Resolve-Path $File).Path
if ($Target -notmatch '^[a-z_][a-z0-9_]*$') {
    throw "Target must be a plain database name (a-z, 0-9, _)."
}

if ($Target -eq "venus" -and -not $Force) {
    Write-Host "This replaces the live Venus database with $File"
    if ((Read-Host "Type RESTORE to continue") -ne "RESTORE") {
        Write-Host "Cancelled."
        return
    }
}

Write-Host "Copying the backup into the Postgres container..."
Invoke-Compose cp $File postgres:/tmp/restore.dump

$coreWasRunning = $false
if ($Target -eq "venus") {
    $stamp = Get-Date -Format "yyyy-MM-dd_HHmmss"
    $safety = Join-Path (Split-Path -Parent $File) "pre-restore-$stamp.dump"
    Write-Host "Saving the current database to $safety ..."
    Invoke-Compose exec -T postgres pg_dump -U venus -d venus -Fc -f /tmp/pre-restore.dump
    Invoke-Compose cp postgres:/tmp/pre-restore.dump $safety

    # Core holds open connections, which would block dropping the database.
    $running = docker compose --project-directory $root --profile server ps --status running --services
    $coreWasRunning = $running -contains "core"
    if ($coreWasRunning) {
        Write-Host "Stopping Core..."
        Invoke-Compose --profile server stop core
    }
}

try {
    Write-Host "Restoring into database '$Target'..."
    Invoke-Compose exec -T postgres dropdb -U venus --if-exists --force $Target
    Invoke-Compose exec -T postgres createdb -U venus $Target
    Invoke-Compose exec -T postgres pg_restore -U venus -d $Target --no-owner --exit-on-error /tmp/restore.dump
    Invoke-Compose exec -T postgres rm -f /tmp/restore.dump /tmp/pre-restore.dump
} finally {
    if ($coreWasRunning) {
        Write-Host "Starting Core again..."
        Invoke-Compose --profile server up -d --wait core
    }
}

Write-Host "Restored $File into '$Target'."
