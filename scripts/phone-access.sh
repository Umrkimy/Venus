#!/usr/bin/env bash
# Open Venus on your phone (or any of your devices) through Tailscale.
# Linux version of phone-access.ps1.
#
#   ./scripts/phone-access.sh
#       Shares the web app (port 3000) as https://<pc>.<tailnet>.ts.net,
#       visible only to devices signed in to your own Tailscale account.
#       Also shares Core (port 9000) on port 9443, for Venus Nodes on your
#       other PCs: VENUS_NODE_CORE_URL=wss://<that name>:9443/nodes/connect
#       Tailscale keeps sharing both after a reboot. Safe to run again.
#
#   ./scripts/phone-access.sh --off
#       Stops sharing.
#
# Needs Tailscale installed and signed in on the PC and the phone, with
# MagicDNS and HTTPS Certificates turned on in the Tailscale admin console
# (DNS page). Nothing is opened to the public internet. If tailscale says
# "access denied", run once: sudo tailscale set --operator=$USER
set -euo pipefail

fail() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

command -v tailscale >/dev/null 2>&1 ||
    fail "Tailscale is not installed. Arch/CachyOS: sudo pacman -S tailscale && sudo systemctl enable --now tailscaled && sudo tailscale up. Others: https://tailscale.com/download"

if [[ "${1:-}" == "--off" ]]; then
    tailscale serve --https=443 off || fail "tailscale serve off failed."
    # Older setups never shared 9443; "handler does not exist" is fine then.
    tailscale serve --https=9443 off >/dev/null 2>&1 || true
    echo "Venus is no longer shared over Tailscale."
    exit 0
fi

status="$(tailscale status --json)"
read_status() { python3 -c "import json, sys; s = json.load(sys.stdin); print($1)" <<<"$status"; }
state="$(read_status 's.get("BackendState", "")')"
[[ "$state" == "Running" ]] ||
    fail "Tailscale is not connected (state: $state). Run 'sudo tailscale up', then run this again."

tailscale serve --bg 3000 ||
    fail "tailscale serve failed. Check that HTTPS Certificates are on in the Tailscale admin console (DNS page)."
tailscale serve --bg --https=9443 9000 || fail "tailscale serve for Core (port 9443) failed."

name="$(read_status 's["Self"]["DNSName"].rstrip(".")')"
echo
echo "Open this on your phone (Tailscale app connected):"
echo "  https://$name"
echo "Venus itself must be running (./start-venus.sh --use or ./start-venus.sh)."
echo "Other PCs (setup-venus --node-only) connect to:"
echo "  wss://$name:9443/nodes/connect"
