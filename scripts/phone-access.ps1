# Open Venus on your phone (or any of your devices) through Tailscale.
#
#   .\scripts\phone-access.ps1
#       Shares the web app (port 3000) as https://<pc>.<tailnet>.ts.net,
#       visible only to devices signed in to your own Tailscale account.
#       Also shares Core (port 9000) on port 9443, for Venus Nodes on your
#       other PCs: VENUS_NODE_CORE_URL=wss://<that name>:9443/nodes/connect
#       Tailscale keeps sharing both after a reboot. Safe to run again.
#
#   .\scripts\phone-access.ps1 -Off
#       Stops sharing.
#
# Needs Tailscale installed and signed in on the PC and the phone, with
# MagicDNS and HTTPS Certificates turned on in the Tailscale admin console
# (DNS page). Nothing is opened to the public internet.
param(
    [switch]$Off
)

$ErrorActionPreference = "Stop"

function Find-Tailscale {
    $command = Get-Command tailscale -ErrorAction SilentlyContinue
    if ($command) { return $command.Source }
    $default = Join-Path $env:ProgramFiles "Tailscale\tailscale.exe"
    if (Test-Path $default) { return $default }
    throw "Tailscale is not installed. Get it from https://tailscale.com/download, sign in, then run this again."
}

$tailscale = Find-Tailscale

if ($Off) {
    & $tailscale serve --https=443 off
    if ($LASTEXITCODE -ne 0) { throw "tailscale serve off failed." }
    # Older setups never shared 9443; "handler does not exist" is fine then.
    $ErrorActionPreference = "Continue"
    & $tailscale serve --https=9443 off 2>&1 | Out-Null
    $ErrorActionPreference = "Stop"
    Write-Host "Venus is no longer shared over Tailscale."
    return
}

$status = & $tailscale status --json | ConvertFrom-Json
if ($status.BackendState -ne "Running") {
    throw "Tailscale is not connected (state: $($status.BackendState)). Open Tailscale, sign in, then run this again."
}

& $tailscale serve --bg 3000
if ($LASTEXITCODE -ne 0) {
    throw "tailscale serve failed. Check that HTTPS Certificates are on in the Tailscale admin console (DNS page)."
}
& $tailscale serve --bg --https=9443 9000
if ($LASTEXITCODE -ne 0) { throw "tailscale serve for Core (port 9443) failed." }

$name = $status.Self.DNSName.TrimEnd(".")
Write-Host ""
Write-Host "Open this on your phone (Tailscale app connected):"
Write-Host "  https://$name"
Write-Host "Venus itself must be running (start-venus-use.cmd or start-venus.cmd)."
Write-Host "Other PCs (setup-venus-node.cmd) connect to:"
Write-Host "  wss://${name}:9443/nodes/connect"
