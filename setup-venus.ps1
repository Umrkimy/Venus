# First-time setup for Venus on Windows. Double-click setup-venus.cmd.
#
# 1. Checks for Docker Desktop and Python 3.11+.
# 2. Writes the three .env files with fresh random secrets (root .env,
#    apps/core/.env, apps/node/.env). Existing files are kept, so running
#    this again never changes your secrets or keys.
# 3. Installs the PC part (apps/node) into apps/node/.venv.
# 4. Downloads the "Hey Venus" speech model (Vosk, about 40 MB).
# 5. Starts Venus in server mode (start-venus.ps1 -Use).
# 6. Asks for your username and password if no account exists yet.
#
# Afterwards start Venus with start-venus-use.cmd.
#
# -NodeOnly (setup-venus-node.cmd) is for another PC that only runs the Node:
# no Docker, no database, no web app, no "Hey Venus". It asks for Core's
# address and a token from Settings, Devices, Add device on the main PC.
param(
    [switch]$NodeOnly
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$voskName = "vosk-model-small-en-us-0.15"
$voskUrl = "https://alphacephei.com/vosk/models/$voskName.zip"

function Write-Step([string]$text) {
    Write-Host ""
    Write-Host "== $text" -ForegroundColor Cyan
}

# Hex only, so a secret is safe inside a database URL.
function New-Secret {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return -join ($bytes | ForEach-Object { $_.ToString("x2") })
}

# Fernet key: 32 random bytes, URL-safe base64 (what VENUS_CORE_SECRET_KEY needs).
function New-FernetKey {
    $bytes = New-Object byte[] 32
    [System.Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
    return [Convert]::ToBase64String($bytes).Replace("+", "-").Replace("/", "_")
}

# One value from a .env file, or "" when the file or the name is missing.
function Get-EnvValue([string]$path, [string]$name) {
    if (-not (Test-Path $path)) { return "" }
    foreach ($line in Get-Content $path) {
        if ($line -match "^\s*$name\s*=(.*)$") { return $Matches[1].Trim() }
    }
    return ""
}

# Writes a new .env file (ASCII: a UTF-8 byte order mark would break the
# first name). Returns $false and keeps the file when it already exists.
function New-EnvFile([string]$path, [string[]]$lines) {
    if (Test-Path $path) {
        Write-Host "Keeping existing $path"
        return $false
    }
    Set-Content -Path $path -Value $lines -Encoding ascii
    Write-Host "Created $path"
    return $true
}

function Find-Python {
    # The py launcher picks a version; plain python is the fallback.
    $candidates = @(@("py", "-3.11"), @("py", "-3.12"), @("py", "-3.13"), @("python"))
    foreach ($candidate in $candidates) {
        $exe = $candidate[0]
        $versionArgs = @($candidate | Select-Object -Skip 1)
        if (-not (Get-Command $exe -ErrorAction SilentlyContinue)) { continue }
        $ok = & $exe @versionArgs -c "import sys; print(sys.version_info >= (3, 11))" 2>$null
        if ($LASTEXITCODE -eq 0 -and $ok -eq "True") { return ,$candidate }
    }
    return $null
}

Write-Host "Venus setup" -ForegroundColor Cyan

# --- 1. Requirements -------------------------------------------------------
Write-Step "Checking requirements"
if (-not $NodeOnly -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw "Docker Desktop is missing. Install it from https://www.docker.com/products/docker-desktop/ and run setup again."
}
$python = Find-Python
if (-not $python) {
    throw "Python 3.11 or newer is missing. Install it from https://www.python.org/downloads/ (tick 'Add python.exe to PATH') and run setup again."
}
Write-Host "Python: $($python -join ' ')"

# --- 2. Settings files -----------------------------------------------------
Write-Step "Writing settings (.env files)"
$rootEnv = Join-Path $root ".env"
$coreEnv = Join-Path $root "apps\core\.env"
$nodeEnv = Join-Path $root "apps\node\.env"
$deviceId = "pc-" + (($env:COMPUTERNAME -replace "[^A-Za-z0-9-]", "").ToLower())

if ($NodeOnly) {
    if (Test-Path $nodeEnv) {
        Write-Host "Keeping existing $nodeEnv"
    } else {
        Write-Host "On the main PC, scripts\domain-access.ps1 or scripts\phone-access.ps1"
        Write-Host "prints the address for other PCs. A plain name like venus.example.com is fine."
        $address = (Read-Host "Core address").Trim()
        if (-not $address) { throw "No Core address given. Run setup-venus-node.cmd again." }
        if ($address -notmatch "^wss?://") { $address = "wss://${address}:9443/nodes/connect" }
        Write-Host "On the main PC: Settings, Devices, Add device. Paste its token here (hidden)."
        $secure = Read-Host "Token" -AsSecureString
        $token = [Runtime.InteropServices.Marshal]::PtrToStringBSTR(
            [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)).Trim()
        if (-not $token) { throw "No token given. Run setup-venus-node.cmd again." }
        New-EnvFile $nodeEnv @(
            "# Made by setup-venus.ps1 -NodeOnly. See apps/node/.env.example.",
            "VENUS_NODE_DEVICE_ID=$deviceId",
            "VENUS_NODE_CORE_DEV_TOKEN=$token",
            "VENUS_NODE_CORE_URL=$address",
            "VENUS_NODE_REAL_ACTIONS=true",
            "# Folder with your code projects, for 'open project X' (optional).",
            "VENUS_NODE_PROJECTS_ROOT=",
            "# Hey Venus runs on the main PC only (for now).",
            "VENUS_NODE_VOICE=false"
        ) | Out-Null
    }
} else {
    $postgresPassword = Get-EnvValue $rootEnv "VENUS_POSTGRES_PASSWORD"
    if (-not $postgresPassword) {
        $postgresPassword = New-Secret
        if (Test-Path $rootEnv) {
            Add-Content -Path $rootEnv -Value "VENUS_POSTGRES_PASSWORD=$postgresPassword" -Encoding ascii
            Write-Host "Added VENUS_POSTGRES_PASSWORD to $rootEnv"
        } else {
            New-EnvFile $rootEnv @(
                "# Docker Compose settings. See .env.example.",
                "VENUS_POSTGRES_PASSWORD=$postgresPassword",
                "# Backups go to ./backups. Better on another drive, for example:",
                "# VENUS_BACKUP_DIR=E:/VenusBackups"
            ) | Out-Null
        }
    } else {
        Write-Host "Keeping existing $rootEnv"
    }

    New-EnvFile $coreEnv @(
        "# Made by setup-venus.ps1. See apps/core/.env.example.",
        "VENUS_CORE_DEV_NODE_TOKEN=$(New-Secret)",
        "VENUS_CORE_DATABASE_URL=postgresql+psycopg://venus:$postgresPassword@127.0.0.1:5432/venus",
        "VENUS_CORE_SECRET_KEY=$(New-FernetKey)",
        "# AI and voice keys: easiest in the web page, Settings. These are fallbacks.",
        "VENUS_CORE_LLM_PROVIDER=",
        "VENUS_CORE_LLM_MODEL=",
        "VENUS_CORE_LLM_API_KEY=",
        "VENUS_CORE_FISH_API_KEY=",
        "VENUS_CORE_FISH_VOICE_ID=",
        "VENUS_CORE_FISH_MODEL="
    ) | Out-Null

    # The Node proves itself to Core with the same token.
    $nodeToken = Get-EnvValue $coreEnv "VENUS_CORE_DEV_NODE_TOKEN"
    New-EnvFile $nodeEnv @(
        "# Made by setup-venus.ps1. See apps/node/.env.example.",
        "VENUS_NODE_DEVICE_ID=$deviceId",
        "VENUS_NODE_CORE_DEV_TOKEN=$nodeToken",
        "VENUS_NODE_CORE_URL=ws://127.0.0.1:9000/nodes/connect",
        "VENUS_NODE_REAL_ACTIONS=true",
        "# Folder with your code projects, for 'open project X' (optional).",
        "VENUS_NODE_PROJECTS_ROOT=",
        "VENUS_NODE_WAKE_PHRASES=hey venus,venus"
    ) | Out-Null
}

# --- 3. PC part (Node) -----------------------------------------------------
Write-Step "Installing the PC part (apps/node)"
$nodeDir = Join-Path $root "apps\node"
$venvPython = Join-Path $nodeDir ".venv\Scripts\python.exe"
Push-Location $nodeDir
try {
    if (-not (Test-Path $venvPython)) {
        $exe = $python[0]
        $versionArgs = @($python | Select-Object -Skip 1)
        & $exe @versionArgs -m venv .venv
        if ($LASTEXITCODE -ne 0) { throw "Could not create apps/node/.venv." }
    }
    # requirements.txt points at ../../packages, so run it from apps/node.
    & $venvPython -m pip install --disable-pip-version-check -q -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw "Installing the PC part failed (see pip's message above)." }
} finally {
    Pop-Location
}
Write-Host "PC part installed."

if ($NodeOnly) {
    # The tray app: connection, orb and tray icon. "Start with Windows" is in its menu.
    Start-Process (Join-Path $nodeDir ".venv\Scripts\pythonw.exe") -ArgumentList "venus.pyw" -WorkingDirectory $nodeDir
    Write-Host ""
    Write-Host "Venus Node is running on this PC." -ForegroundColor Green
    Write-Host "- Tray icon menu: Start with Windows."
    Write-Host "- On the main PC, the chat shows a PC picker once two PCs are online."
    Write-Host "- Log: apps\node\data\venus-node.log"
    return
}

# --- 4. Speech model for "Hey Venus" ---------------------------------------
Write-Step "Speech model for 'Hey Venus'"
$modelsDir = Join-Path $nodeDir "models"
if (Test-Path (Join-Path $modelsDir $voskName)) {
    Write-Host "Already downloaded."
} else {
    New-Item -ItemType Directory -Force $modelsDir | Out-Null
    $zip = Join-Path $modelsDir "$voskName.zip"
    Write-Host "Downloading $voskUrl (about 40 MB)..."
    $ProgressPreference = "SilentlyContinue"  # the progress bar makes it 10x slower
    Invoke-WebRequest -Uri $voskUrl -OutFile $zip -UseBasicParsing
    Expand-Archive -Path $zip -DestinationPath $modelsDir -Force
    Remove-Item $zip
    Write-Host "Saved to apps/node/models/$voskName"
}

# --- 5. Start Venus --------------------------------------------------------
Write-Step "Starting Venus (first build takes a few minutes)"
& (Join-Path $root "start-venus.ps1") -Use

# --- 6. Your account -------------------------------------------------------
Write-Step "Your account"
$owners = docker compose --project-directory $root exec -T postgres `
    psql -U venus -d venus -tAc "select count(*) from owner_accounts"
if ($LASTEXITCODE -ne 0) { throw "Could not read the database." }
if ([int]$owners -gt 0) {
    Write-Host "An account already exists. Sign in at http://localhost:3000"
} else {
    Write-Host "Choose a username and a password (12+ characters) for the web page."
    for ($try = 1; $try -le 3; $try++) {
        $username = (Read-Host "Username").Trim()
        if (-not $username) {
            if ($try -eq 3) { throw "No account created. Run setup-venus.cmd again." }
            Write-Host "Username cannot be empty."
            continue
        }
        # Interactive, so the password is typed hidden inside the container.
        docker compose --project-directory $root exec core `
            python -m features.auth.create_owner $username
        if ($LASTEXITCODE -eq 0) { break }
        if ($try -eq 3) { throw "No account created. Run setup-venus.cmd again." }
        Write-Host "Try again."
    }
}

Write-Host ""
Write-Host "Venus is ready." -ForegroundColor Green
Write-Host "- Open http://localhost:3000 and sign in."
Write-Host "- Settings: add an OpenAI key for chat and a Fish Audio key for her voice."
Write-Host "  Without a key Venus still opens apps and sites from typed commands."
Write-Host "- Everyday start: start-venus-use.cmd (tray icon menu: Start with Windows)."
