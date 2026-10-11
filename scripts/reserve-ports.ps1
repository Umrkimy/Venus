# Keep Windows from taking Venus's ports after a reboot. Run once, as admin.
#
#   .\scripts\reserve-ports.ps1
#
# At each boot Windows (Hyper-V / WinNAT, used by Docker) blocks random port
# ranges. When one covers 3000, 5432, 9000 or 9443, Venus fails with "port in
# use" or "access forbidden". Reserving the ports ourselves stops that for
# good; Venus can still use them. Safe to run again.
#
# First quit Docker Desktop (whale icon > Quit) and the Venus tray app
# (dot by the clock > Quit): Windows only reserves ports nothing is using.
$ErrorActionPreference = "Stop"
$ports = 3000, 5432, 9000, 9443

$admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()
    ).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $admin) {
    Write-Host "Run this in an admin terminal (right-click PowerShell > Run as administrator)."
    exit 1
}

# Lines like "      9443        9443" (start, end); "*" marks ranges we added.
# @() keeps a single range as one pair, not two loose numbers.
$reserved = @(netsh interface ipv4 show excludedportrange protocol=tcp store=persistent |
    ForEach-Object { if ($_ -match '^\s*(\d+)\s+(\d+)') { , @([int]$Matches[1], [int]$Matches[2]) } })
$missing = $ports | Where-Object {
    $port = $_
    -not ($reserved | Where-Object { $_[0] -le $port -and $port -le $_[1] })
}
if (-not $missing) {
    Write-Host "Already reserved: $($ports -join ', '). Nothing to do."
    exit 0
}

$busy = $missing | Where-Object { Get-NetTCPConnection -LocalPort $_ -State Listen -ErrorAction SilentlyContinue }
if ($busy) {
    Write-Host "Still in use: $($busy -join ', '). Quit Docker Desktop and the Venus tray app, then run again."
    exit 1
}

# WinNAT holds today's random ranges; stopping it frees them while we reserve.
net stop winnat | Out-Null
try {
    foreach ($port in $missing) {
        netsh interface ipv4 add excludedportrange protocol=tcp startport=$port numberofports=1 store=persistent | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "Could not reserve port $port." }
        Write-Host "Reserved $port"
    }
} finally {
    net start winnat | Out-Null
}
Write-Host "Done. Start Docker Desktop and Venus again (start-venus-use.cmd)."
