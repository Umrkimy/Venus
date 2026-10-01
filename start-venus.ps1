# Starts everything Venus needs for local development:
# Postgres in Docker, then Core, Node, and the web page in their own windows.
# Close a window to stop that part. Postgres keeps running until
# `docker compose stop postgres`.

$root = $PSScriptRoot

function Test-DockerRunning {
    docker info *> $null
    return $LASTEXITCODE -eq 0
}

function Test-PortInUse([int]$port) {
    return [bool](Get-NetTCPConnection -LocalPort $port -State Listen `
        -ErrorAction SilentlyContinue)
}

function Test-NodeRunning {
    $pythons = Get-CimInstance Win32_Process -Filter "Name = 'python.exe'"
    return [bool]($pythons | Where-Object { $_.CommandLine -like "*venus_node*" })
}

function Start-Window([string]$title, [string]$folder, [string]$command) {
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

# Core reads Postgres at startup, so wait until the healthcheck passes.
Write-Host "Starting Postgres..."
docker compose --project-directory $root up -d --wait postgres
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
if (Test-NodeRunning) {
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

Write-Host "Venus is starting. Open http://localhost:3000 in a few seconds."
