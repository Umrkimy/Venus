# Open Venus at your own domain (for example https://venus.example.com),
# still only for devices in your Tailscale network.
#
#   .\scripts\domain-access.ps1
#       Downloads Caddy (asks first), stops the Tailscale share from
#       phone-access.ps1 (Caddy takes its place on port 443) and restarts
#       the Venus tray app, which keeps Caddy running from now on.
#
# Needs in the .env in the repository root (see README "Your own domain"):
#   VENUS_DOMAIN          your domain, DNS A record -> this PC's Tailscale address
#   CLOUDFLARE_API_TOKEN  Cloudflare token with "Edit zone DNS" for that domain
# To stop: empty VENUS_DOMAIN, Quit Venus in the tray and start it again,
# then .\scripts\phone-access.ps1 for the ts.net address.
param(
    # Download without asking.
    [switch]$Yes
)

$ErrorActionPreference = "Stop"
$root = Split-Path $PSScriptRoot -Parent
$envFile = Join-Path $root ".env"
$caddyDir = Join-Path $root "tools\caddy"
$caddy = Join-Path $caddyDir "caddy.exe"
$caddyfile = Join-Path $PSScriptRoot "domain\Caddyfile"
$download = "https://caddyserver.com/api/download?os=windows&arch=amd64&p=github.com%2Fcaddy-dns%2Fcloudflare"

function Read-EnvValue([string]$name) {
    if (-not (Test-Path $envFile)) { return "" }
    $line = Get-Content $envFile | Where-Object { $_ -match "^\s*$name\s*=" } | Select-Object -Last 1
    if (-not $line) { return "" }
    return ($line -split "=", 2)[1].Trim().Trim('"').Trim("'")
}

function Find-Tailscale {
    $command = Get-Command tailscale -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $default = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $default) { return $default }
    throw "Tailscale is not installed. Get it from https://tailscale.com/download, sign in, then run this again."
}

function Get-TrayApp {
    Get-CimInstance Win32_Process -Filter "Name = 'pythonw.exe' or Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*venus.pyw*" }
}

$domain = Read-EnvValue "VENUS_DOMAIN"
if (-not $domain) { throw "Set VENUS_DOMAIN in $envFile first (see README 'Your own domain')." }
# Only checked for being set: the token is never printed.
if (-not (Read-EnvValue "CLOUDFLARE_API_TOKEN")) { throw "Set CLOUDFLARE_API_TOKEN in $envFile first." }

$tailscale = Find-Tailscale
$ip = (& $tailscale ip -4 | Select-Object -First 1)
if ($LASTEXITCODE -ne 0 -or -not $ip) { throw "Tailscale is not connected. Open Tailscale, sign in, then run this again." }

$dns = Resolve-DnsName $domain -Type A -Server 1.1.1.1 -ErrorAction SilentlyContinue
if (-not ($dns | Where-Object { $_.IPAddress -eq $ip })) {
    Write-Warning "$domain does not point to $ip (this PC's Tailscale address) yet. Add a DNS A record, DNS only."
}

if (-not (Test-Path $caddy)) {
    if (-not $Yes) {
        $answer = Read-Host "Download Caddy with the Cloudflare module (about 40 MB) from caddyserver.com? [y/N]"
        if ($answer -notmatch "^[yY]") { throw "Caddy is needed for your own domain. Stopped." }
    }
    New-Item -ItemType Directory -Force $caddyDir | Out-Null
    Write-Host "Downloading Caddy..."
    $ProgressPreference = "SilentlyContinue"  # The progress bar makes the download much slower.
    Invoke-WebRequest $download -OutFile $caddy
}
if (-not (& $caddy list-modules | Select-String "dns.providers.cloudflare")) {
    throw "$caddy has no Cloudflare module. Delete it and run this again."
}

$env:VENUS_TAILNET_IP = $ip
# Caddy logs to stderr; "Stop" would treat its first line as an error.
$ErrorActionPreference = "Continue"
$check = & $caddy validate --config $caddyfile --adapter caddyfile --envfile $envFile 2>&1
$ErrorActionPreference = "Stop"
if ($LASTEXITCODE -ne 0) {
    $check | Write-Host
    throw "The Caddyfile did not validate. See the messages above."
}

# tailscale serve holds ports 443 and 9443 on the Tailscale address; Caddy needs them.
# It says "handler does not exist" when already off, so errors are ignored.
$ErrorActionPreference = "Continue"
& $tailscale serve --https=443 off 2>&1 | Out-Null
& $tailscale serve --https=9443 off 2>&1 | Out-Null
$ErrorActionPreference = "Stop"

# The tray app starts Caddy when it starts, so restart it.
$node = Join-Path $root "apps\node"
if (Get-TrayApp) {
    # From the Node folder, where Python finds venus_node.
    Push-Location $node
    & "$node\.venv\Scripts\python.exe" -m venus_node.app.quit | Out-Null
    Pop-Location
    $waited = 0
    while (Get-TrayApp) {
        if ($waited -ge 20) { throw "The Venus tray app did not quit. Quit it from the tray and run this again." }
        Start-Sleep -Seconds 1
        $waited += 1
    }
}
Start-Process "$node\.venv\Scripts\pythonw.exe" -ArgumentList "venus.pyw" -WorkingDirectory $node

Write-Host ""
Write-Host "Open this on your phone (Tailscale app connected):"
Write-Host "  https://$domain"
Write-Host "The first start gets a certificate, which can take a minute."
Write-Host "Caddy's messages: apps\node\data\caddy.log"
Write-Host "Other PCs (setup-venus-node.cmd) connect to:"
Write-Host "  wss://${domain}:9443/nodes/connect"
