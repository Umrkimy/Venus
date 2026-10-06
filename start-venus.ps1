# Starts everything Venus needs for local development:
# Postgres in Docker, then Core, Node, the web page and the "Hey Venus"
# listener, as tabs of one Windows Terminal window (separate windows if
# Windows Terminal is missing). Close a tab to stop that part, or the
# window to stop them all. Postgres keeps running until
# `docker compose stop postgres`.
#
# -Use (start-venus-use.cmd): everyday server mode, lighter on RAM.
# Postgres, Core and the built web app run in Docker
# (`docker compose --profile server`), restart by themselves and come back
# after a reboot once Docker Desktop starts. The hidden tray app replaces
# the Node/Listen tabs. Code changes: run this again (it rebuilds).

param([switch]$Use)

$root = $PSScriptRoot

if (-not (Test-Path "$root\apps\core\.env") -or -not (Test-Path "$root\apps\node\.venv")) {
    throw "Venus is not set up yet. Run setup-venus.cmd first."
}

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

function Test-PortInUse([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen `
        -ErrorAction SilentlyContinue)
}

function Test-PythonRunning([string]$module) {
    $pythons = Get-CimInstance Win32_Process -Filter "Name = 'python.exe' or Name = 'pythonw.exe'"
    return [bool]($pythons | Where-Object { $_.CommandLine -like "*$module*" })
}

$hasTerminal = [bool](Get-Command wt.exe -ErrorAction SilentlyContinue)
$firstTab = $true
# Windows Terminal can't find plain "powershell" (error 0x80070002): use the full path.
$powershell = "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe"

function Start-Window([string]$title, [string]$folder, [string]$command) {
    if ($hasTerminal) {
        # One Windows Terminal window named "venus", one tab per part.
        # Our commands have no ';' (Windows Terminal would split on it).
        $tab = "-w venus new-tab --title `"Venus $title`" --suppressApplicationTitle " +
            "-d `"$folder`" `"$powershell`" -NoExit -Command `"$command`""
        Start-Process wt.exe -ArgumentList $tab
        # Give the first call time to create the window, so the rest join it.
        if ($script:firstTab) { Start-Sleep -Milliseconds 1500; $script:firstTab = $false }
        return
    }
    $script = "`$Host.UI.RawUI.WindowTitle = 'Venus $title'; $command"
    Start-Process powershell -WorkingDirectory $folder `
        -ArgumentList "-NoExit", "-Command", $script
}

if (-not (Test-DockerRunning)) {
    Write-Host "Starting Docker Desktop..."
    Start-Process "$env:ProgramFiles\Docker\Docker\Docker Desktop.exe"
    $waited = 0
    while (-not (Test-DockerRunning)) {
        if ($waited -ge 120) {
            throw "Docker did not start within 2 minutes. Open Docker Desktop and try again."
        }
        Start-Sleep -Seconds 3
        $waited += 3
    }
}

if ($Use) {
    # Server mode: Postgres, Core and web as containers. --build picks up
    # code changes; --wait returns once all healthchecks pass.
    Write-Host "Starting Venus server (Docker)..."
    docker compose --project-directory $root --profile server up -d --build --wait
    if ($LASTEXITCODE -ne 0) {
        throw "Server mode did not start. Check 'docker compose --profile server logs'."
    }
    # The tray app: connection, "Hey Venus", orb and tray icon, no window.
    if (Test-PythonRunning "venus.pyw") {
        Write-Host "Venus tray app is already running."
    } else {
        Start-Process "$root\apps\node\.venv\Scripts\pythonw.exe" `
            -ArgumentList "venus.pyw" -WorkingDirectory "$root\apps\node"
    }
    Write-Host "Venus is running. Open http://localhost:3000"
    return
}

# Dev mode uses the same ports as server mode: stop its containers first.
docker compose --project-directory $root --profile server stop core web *> $null

# Core reads Postgres at startup, so wait until the healthcheck passes.
Write-Host "Starting Postgres and backups..."
docker compose --project-directory $root up -d --wait postgres backup
if ($LASTEXITCODE -ne 0) {
    throw "Postgres did not start. Check 'docker compose logs postgres'."
}

# Skip anything already running, so a second click does not start copies.
if (Test-PortInUse 9000) {
    Write-Host "Core is already running on port 9000."
} else {
    Start-Window "Core" "$root\apps\core" `
        ".\.venv\Scripts\python.exe -m uvicorn main:app --port 9000 --reload"
}

# The Node keeps retrying until Core is up, so it can start right away.
if (Test-PythonRunning "venus_node.dev_connect") {
    Write-Host "Node is already running."
} else {
    Start-Window "Node" "$root\apps\node" `
        ".\.venv\Scripts\python.exe -m venus_node.dev_connect"
}

if (Test-PortInUse 3000) {
    Write-Host "Web is already running on port 3000."
} else {
    Start-Window "Web" "$root\apps\web" "npm run dev"
}

# "Hey Venus": only talks to Core after a wake, so it can start right away.
# It shows the listening circle; a missing Vosk model is explained in its window.
if (Test-PythonRunning "venus_node.cli.listen") {
    Write-Host "Hey Venus listener is already running."
} else {
    Start-Window "Listen" "$root\apps\node" `
        ".\.venv\Scripts\python.exe -m venus_node.cli.listen"
}

Write-Host "Venus is starting. Open http://localhost:3000 in a few seconds."
