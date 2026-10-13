#!/usr/bin/env bash
# Open Venus at your own domain (for example https://venus.example.com),
# still only for devices in your Tailscale network. Linux version of
# domain-access.ps1.
#
#   ./scripts/domain-access.sh [--yes]
#       Downloads Caddy with the Cloudflare module (asks first, --yes skips
#       the question), stops the Tailscale share from phone-access.sh (Caddy
#       takes its place on port 443) and restarts the Venus tray app, which
#       keeps Caddy running from now on.
#
# Needs in the .env in the repository root (see guide/remote-access.md):
#   VENUS_DOMAIN          your domain, DNS A record -> this PC's Tailscale address
#   CLOUDFLARE_API_TOKEN  Cloudflare token with "Edit zone DNS" for that domain
# Caddy listens on ports 443 and 9443 as you, not root, so allow that once:
#   sudo setcap cap_net_bind_service=+ep tools/caddy/caddy
# To stop: empty VENUS_DOMAIN, quit Venus in the tray and start it again,
# then ./scripts/phone-access.sh for the ts.net address.
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
env_file="$root/.env"
caddy_dir="$root/tools/caddy"
caddy="$caddy_dir/caddy"
caddyfile="$root/scripts/domain/Caddyfile"
node_dir="$root/apps/node"
node_python="$node_dir/.venv/bin/python"

fail() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }
env_value() {
    [[ -f "$env_file" ]] || return 0
    sed -n "s/^[[:space:]]*$1[[:space:]]*=\(.*\)$/\1/p" "$env_file" | tail -n 1 | tr -d "\"'" | xargs
}

case "$(uname -m)" in
    x86_64) arch=amd64 ;;
    aarch64 | arm64) arch=arm64 ;;
    *) fail "No Caddy download for $(uname -m) here; put a caddy with the Cloudflare module in $caddy yourself." ;;
esac
os=linux
[[ "$(uname -s)" == "Darwin" ]] && os=darwin
download="https://caddyserver.com/api/download?os=$os&arch=$arch&p=github.com%2Fcaddy-dns%2Fcloudflare"

domain="$(env_value VENUS_DOMAIN)"
[[ -n "$domain" ]] || fail "Set VENUS_DOMAIN in $env_file first (see guide/remote-access.md)."
# Only checked for being set: the token is never printed.
[[ -n "$(env_value CLOUDFLARE_API_TOKEN)" ]] || fail "Set CLOUDFLARE_API_TOKEN in $env_file first."

command -v tailscale >/dev/null 2>&1 || fail "Tailscale is not installed. See scripts/phone-access.sh."
ip="$(tailscale ip -4 2>/dev/null | head -n 1)" || true
[[ -n "$ip" ]] || fail "Tailscale is not connected. Run 'sudo tailscale up', then run this again."

if command -v getent >/dev/null 2>&1 && ! getent ahostsv4 "$domain" | grep -q "^$ip "; then
    echo "Warning: $domain does not point to $ip (this PC's Tailscale address) yet. Add a DNS A record, DNS only."
fi

if [[ ! -x "$caddy" ]]; then
    if [[ "${1:-}" != "--yes" ]]; then
        read -r -p "Download Caddy with the Cloudflare module (about 40 MB) from caddyserver.com? [y/N] " answer
        [[ "$answer" =~ ^[yY] ]] || fail "Caddy is needed for your own domain. Stopped."
    fi
    mkdir -p "$caddy_dir"
    echo "Downloading Caddy..."
    curl -fL --progress-bar -o "$caddy" "$download"
    chmod +x "$caddy"
    echo "Now allow it to use ports 443 and 9443 (asks for your password):"
    sudo setcap cap_net_bind_service=+ep "$caddy"
fi
"$caddy" list-modules | grep -q "dns.providers.cloudflare" ||
    fail "$caddy has no Cloudflare module. Delete it and run this again."

if ! VENUS_TAILNET_IP="$ip" "$caddy" validate --config "$caddyfile" --adapter caddyfile --envfile "$env_file"; then
    fail "The Caddyfile did not validate. See the messages above."
fi

# tailscale serve holds ports 443 and 9443 on the Tailscale address; Caddy needs them.
tailscale serve --https=443 off >/dev/null 2>&1 || true
tailscale serve --https=9443 off >/dev/null 2>&1 || true

# The tray app starts Caddy when it starts, so restart it.
if pgrep -f "venus.pyw" >/dev/null; then
    (cd "$node_dir" && "$node_python" -m venus_node.app.quit >/dev/null) || true
    for _ in $(seq 1 20); do
        pgrep -f "venus.pyw" >/dev/null || break
        sleep 1
    done
    pgrep -f "venus.pyw" >/dev/null && fail "The Venus tray app did not quit. Quit it from the tray and run this again."
fi
(cd "$node_dir" && mkdir -p data && nohup "$node_python" venus.pyw --hidden >data/startup.log 2>&1 &)

echo
echo "Open this on your phone (Tailscale app connected):"
echo "  https://$domain"
echo "The first start gets a certificate, which can take a minute."
echo "Caddy's messages: apps/node/data/caddy.log"
echo "Other PCs (setup-venus --node-only) connect to:"
echo "  wss://$domain:9443/nodes/connect"
