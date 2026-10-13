#!/usr/bin/env bash
# First-time setup for Venus on Linux (tested on Arch/CachyOS and Debian/Ubuntu)
# and macOS (Docker Desktop + Python from python.org or Homebrew).
# Run once after cloning:  ./setup-venus.sh
#
# 1. Checks for Docker (with compose) and Python 3.11+.
# 2. Writes the three .env files with fresh random secrets (root .env,
#    apps/core/.env, apps/node/.env). Existing files are kept, so running
#    this again never changes your secrets or keys.
# 3. Installs the PC part (apps/node) into apps/node/.venv.
# 4. Downloads the "Hey Venus" speech model (Vosk, about 40 MB).
# 5. Starts Venus in server mode (./start-venus.sh --use).
# 6. Asks for your username and password if no account exists yet.
#
# Afterwards start Venus with ./start-venus.sh --use
#
# --node-only is for another PC that only runs the Node: no Docker, no
# database, no web app, no "Hey Venus". It asks for Core's address and a
# token from Settings, Devices, Add device on the main PC.
#
# System packages the PC part needs (the script tells you if one is missing):
#   Arch/CachyOS:  sudo pacman -S --needed python tk portaudio libnotify
#   Debian/Ubuntu: sudo apt install python3-venv python3-tk libportaudio2 libnotify-bin
#   macOS:         Python from python.org (tkinter included), or brew install python python-tk
set -euo pipefail

root="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
vosk_name="vosk-model-small-en-us-0.15"
vosk_url="https://alphacephei.com/vosk/models/$vosk_name.zip"
node_only=false
[[ "${1:-}" == "--node-only" ]] && node_only=true

# What to install differs per system; only the hints change, not the steps.
if [[ "$(uname -s)" == "Darwin" ]]; then
    docker_hint="Install Docker Desktop from https://www.docker.com/products/docker-desktop/ and open it once."
    docker_run_hint="Open Docker Desktop and wait until it says it's running."
    python_hint="Install it from https://www.python.org/downloads/ (or: brew install python python-tk)."
    tk_hint="Use Python from python.org, or: brew install python-tk."
    audio_hint="brew install portaudio"
else
    docker_hint="Arch/CachyOS: sudo pacman -S docker docker-compose && sudo systemctl enable --now docker."
    docker_run_hint="Try: sudo systemctl enable --now docker && sudo usermod -aG docker \$USER (then log out and in)."
    python_hint="Arch/CachyOS: sudo pacman -S python. Debian/Ubuntu: sudo apt install python3 python3-venv."
    tk_hint="Arch: sudo pacman -S tk. Debian/Ubuntu: sudo apt install python3-tk."
    audio_hint="Arch: sudo pacman -S portaudio. Debian/Ubuntu: sudo apt install libportaudio2."
fi

step() { printf '\n\033[36m== %s\033[0m\n' "$1"; }
fail() { printf '\033[31m%s\033[0m\n' "$1" >&2; exit 1; }

# A Python 3.11+ that can make a venv (Debian splits ensurepip into python3-venv).
find_python() {
    local candidate
    for candidate in python3.13 python3.12 python3.11 python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys, venv, ensurepip; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
            command -v "$candidate"
            return 0
        fi
    done
    return 1
}

# Hex only, so a secret is safe inside a database URL.
new_secret() { "$python" -c 'import secrets; print(secrets.token_hex(32))'; }
# Fernet key: 32 random bytes, URL-safe base64 (what VENUS_CORE_SECRET_KEY needs).
new_fernet_key() { "$python" -c 'import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())'; }

# One value from a .env file, or "" when the file or the name is missing.
env_value() {
    [[ -f "$1" ]] || return 0
    sed -n "s/^[[:space:]]*$2[[:space:]]*=\(.*\)$/\1/p" "$1" | tail -n 1 | xargs
}

# Writes a new .env file (private to you). Keeps the file when it already exists.
new_env_file() {
    local path="$1"
    shift
    if [[ -f "$path" ]]; then
        echo "Keeping existing $path"
        return 0
    fi
    (umask 077 && printf '%s\n' "$@" >"$path")
    echo "Created $path"
}

echo "Venus setup"

# --- 1. Requirements -------------------------------------------------------
step "Checking requirements"
if ! $node_only; then
    command -v docker >/dev/null 2>&1 ||
        fail "Docker is missing. $docker_hint Then run setup again."
    docker compose version >/dev/null 2>&1 ||
        fail "Docker Compose is missing. Arch/CachyOS: sudo pacman -S docker-compose. Debian/Ubuntu: sudo apt install docker-compose-plugin. Mac: it comes with Docker Desktop."
    docker info >/dev/null 2>&1 ||
        fail "Docker isn't running or you can't use it. $docker_run_hint"
fi
python="$(find_python)" || fail "Python 3.11 or newer (with venv) is missing. $python_hint"
echo "Python: $python"
"$python" -c 'import tkinter' 2>/dev/null ||
    echo "Note: tkinter is missing, so the orb window won't show. $tk_hint"

# --- 2. Settings files -----------------------------------------------------
step "Writing settings (.env files)"
root_env="$root/.env"
core_env="$root/apps/core/.env"
node_env="$root/apps/node/.env"
# uname -n: Arch has no hostname command by default.
device_id="pc-$(uname -n | tr -cd 'A-Za-z0-9-' | tr '[:upper:]' '[:lower:]')"

if $node_only; then
    if [[ -f "$node_env" ]]; then
        echo "Keeping existing $node_env"
    else
        echo "On the main PC, scripts/phone-access (or domain-access) prints the address for other PCs."
        echo "A plain name like venus.example.com is fine."
        read -r -p "Core address: " address
        [[ -n "$address" ]] || fail "No Core address given. Run ./setup-venus.sh --node-only again."
        [[ "$address" =~ ^wss?:// ]] || address="wss://${address}:9443/nodes/connect"
        echo "On the main PC: Settings, Devices, Add device. Paste its token here (hidden)."
        read -r -s -p "Token: " token
        echo
        [[ -n "$token" ]] || fail "No token given. Run ./setup-venus.sh --node-only again."
        new_env_file "$node_env" \
            "# Made by setup-venus.sh --node-only. See apps/node/.env.example." \
            "VENUS_NODE_DEVICE_ID=$device_id" \
            "VENUS_NODE_CORE_DEV_TOKEN=$token" \
            "VENUS_NODE_CORE_URL=$address" \
            "VENUS_NODE_REAL_ACTIONS=true" \
            "# Folder with your code projects, for 'open project X' (optional)." \
            "VENUS_NODE_PROJECTS_ROOT=" \
            "# Hey Venus runs on the main PC only (for now)." \
            "VENUS_NODE_VOICE=false"
    fi
else
    postgres_password="$(env_value "$root_env" VENUS_POSTGRES_PASSWORD)"
    if [[ -z "$postgres_password" ]]; then
        postgres_password="$(new_secret)"
        if [[ -f "$root_env" ]]; then
            echo "VENUS_POSTGRES_PASSWORD=$postgres_password" >>"$root_env"
            echo "Added VENUS_POSTGRES_PASSWORD to $root_env"
        else
            new_env_file "$root_env" \
                "# Docker Compose settings. See .env.example." \
                "VENUS_POSTGRES_PASSWORD=$postgres_password" \
                "# Backups go to ./backups. Better on another drive, for example:" \
                "# VENUS_BACKUP_DIR=/mnt/backup/venus"
        fi
    else
        echo "Keeping existing $root_env"
    fi

    new_env_file "$core_env" \
        "# Made by setup-venus.sh. See apps/core/.env.example." \
        "VENUS_CORE_DEV_NODE_TOKEN=$(new_secret)" \
        "VENUS_CORE_DATABASE_URL=postgresql+psycopg://venus:$postgres_password@127.0.0.1:5432/venus" \
        "VENUS_CORE_SECRET_KEY=$(new_fernet_key)" \
        "# AI and voice keys: easiest in the web page, Settings. These are fallbacks." \
        "VENUS_CORE_LLM_PROVIDER=" \
        "VENUS_CORE_LLM_MODEL=" \
        "VENUS_CORE_LLM_API_KEY=" \
        "VENUS_CORE_FISH_API_KEY=" \
        "VENUS_CORE_FISH_VOICE_ID=" \
        "VENUS_CORE_FISH_MODEL="

    # The Node proves itself to Core with the same token.
    node_token="$(env_value "$core_env" VENUS_CORE_DEV_NODE_TOKEN)"
    # The one personal value; asked here so nobody has to edit .env by hand.
    projects=""
    if [[ ! -f "$node_env" ]]; then
        echo "Venus can open your code projects in VS Code ('open project venus')."
        read -r -p "Folder with your code projects (press Enter to skip): " projects
        projects="${projects/#\~/$HOME}"
    fi
    if [[ -n "$projects" && ! -d "$projects" ]]; then
        echo "That folder doesn't exist, skipped. You can set VENUS_NODE_PROJECTS_ROOT in apps/node/.env later."
        projects=""
    fi
    new_env_file "$node_env" \
        "# Made by setup-venus.sh. See apps/node/.env.example." \
        "VENUS_NODE_DEVICE_ID=$device_id" \
        "VENUS_NODE_CORE_DEV_TOKEN=$node_token" \
        "VENUS_NODE_CORE_URL=ws://127.0.0.1:9000/nodes/connect" \
        "VENUS_NODE_REAL_ACTIONS=true" \
        "# Folder with your code projects, for 'open project X' (optional)." \
        "VENUS_NODE_PROJECTS_ROOT=$projects" \
        "VENUS_NODE_WAKE_PHRASES=hey venus,venus"
fi

# --- 3. PC part (Node) -----------------------------------------------------
step "Installing the PC part (apps/node)"
node_dir="$root/apps/node"
venv_python="$node_dir/.venv/bin/python"
if [[ ! -x "$venv_python" ]]; then
    "$python" -m venv "$node_dir/.venv" ||
        fail "Could not create apps/node/.venv. Debian/Ubuntu: sudo apt install python3-venv."
fi
# requirements.txt points at ../../packages, so run it from apps/node.
(cd "$node_dir" && "$venv_python" -m pip install --disable-pip-version-check -q -r requirements.txt) ||
    fail "Installing the PC part failed (see pip's message above)."
"$venv_python" -c 'import sounddevice' 2>/dev/null ||
    echo "Note: PortAudio is missing, so Venus can't use the mic. $audio_hint"
echo "PC part installed."

if $node_only; then
    # The tray app: connection, orb and tray icon. "Start at login" is in its menu.
    (cd "$node_dir" && mkdir -p data && nohup "$venv_python" venus.pyw --hidden >data/startup.log 2>&1 &)
    echo
    printf '\033[32mVenus Node is running on this PC.\033[0m\n'
    echo "- Tray icon menu: Start at login."
    echo "- On the main PC, the chat shows a PC picker once two PCs are online."
    echo "- Log: apps/node/data/venus-node.log"
    exit 0
fi

# --- 4. Speech model for "Hey Venus" ---------------------------------------
step "Speech model for 'Hey Venus'"
models_dir="$node_dir/models"
if [[ -d "$models_dir/$vosk_name" ]]; then
    echo "Already downloaded."
else
    mkdir -p "$models_dir"
    echo "Downloading $vosk_url (about 40 MB)..."
    curl -fL --progress-bar -o "$models_dir/$vosk_name.zip" "$vosk_url"
    # Python unzips it, so the unzip tool isn't needed.
    "$python" -m zipfile -e "$models_dir/$vosk_name.zip" "$models_dir"
    rm "$models_dir/$vosk_name.zip"
    echo "Saved to apps/node/models/$vosk_name"
fi

# --- 5. Start Venus --------------------------------------------------------
step "Starting Venus (first build takes a few minutes)"
"$root/start-venus.sh" --use

# --- 6. Your account -------------------------------------------------------
step "Your account"
owners="$(docker compose --project-directory "$root" exec -T postgres \
    psql -U venus -d venus -tAc "select count(*) from owner_accounts")" || fail "Could not read the database."
if [[ "${owners//[[:space:]]/}" -gt 0 ]]; then
    echo "An account already exists. Sign in at http://localhost:3000"
else
    echo "Choose a username and a password (12+ characters) for the web page."
    for try in 1 2 3; do
        read -r -p "Username: " username
        if [[ -z "$username" ]]; then
            [[ $try -eq 3 ]] && fail "No account created. Run ./setup-venus.sh again."
            echo "Username cannot be empty."
            continue
        fi
        # Interactive, so the password is typed hidden inside the container.
        if docker compose --project-directory "$root" exec core python -m features.auth.create_owner "$username"; then
            break
        fi
        [[ $try -eq 3 ]] && fail "No account created. Run ./setup-venus.sh again."
        echo "Try again."
    done
fi

echo
printf '\033[32mVenus is ready.\033[0m\n'
echo "- Open http://localhost:3000 and sign in."
echo "- Settings: add an OpenAI key for chat and a Fish Audio key for her voice."
echo "  Without a key Venus still opens apps and sites from typed commands."
echo "- Everyday start: ./start-venus.sh --use (tray icon menu: Start at login)."
