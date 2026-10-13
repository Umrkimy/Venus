# Venus

My own assistant that lives on my PC. I say "Hey Venus", she opens my apps,
sites and code projects, chats with me, remembers stuff I tell her and talks
back. There's a 3D version of her on the web page too.

I started this to learn how real apps are built (a server, a database, a web
UI, a desktop app talking to each other) instead of just doing tutorials.
It's self-hosted: everything runs on your own PC, nothing is hosted for you,
and you bring your own API keys. If you want your own Venus, clone it and
follow the setup below.

Works on **Windows 10/11** and **Linux** (I'm moving to CachyOS, so Linux gets
the same features).

## What she can do

Type these in the chat, or say "Hey Venus" first and then say them.

| You say | What happens |
| --- | --- |
| `open spotify` | Opens any app from your Start menu (Windows) or app menu (Linux) |
| `open github.com` | Opens a link in your default browser |
| `youtube lofi beats` | Searches YouTube. Also `google ...` and `netflix ...` |
| `open project venus` | Opens that folder from your projects folder in VS Code |
| `remember I have class at 9 on mondays` | Saves it. She uses it later in chats |
| `what should I cook tonight?` | Normal chat with the AI (Luna) |
| `stop Venus` | Cuts her off mid-sentence |
| `go to sleep` | Stops the conversation, back to waiting for "Hey Venus" |
| `mute the mic` | Mic off until you unmute it (tray menu or the web orb) |
| `thank you Venus` / `bye` | Ends the voice conversation |

You can add your own shortcuts too (Settings, Shortcuts), like `comix` for a
site you open all the time.

PC actions ask before running (an Approve button in the chat). If that gets
annoying, Settings, General, switch to **Full** and she just does it. She can
only open apps from your menu, http(s) links and folders in your projects
folder, nothing else.

Other things in there:

- **Voice**: "Hey Venus" wake word runs offline on your PC (Vosk). Her voice
  comes from [Fish Audio](https://fish.audio/), and the web page has a mic
  button too.
- **3D Venus**: a VRM model in the chat, visual-novel style. Upload your own
  `.vrm` model and `.vrma` moves in Settings, 3D model.
- **Personality**: change how she talks in Settings, Personality.
- **Memory**: see and edit everything she remembers.
- **Usage**: how many tokens and how much money each OpenAI call cost.
- **Phone**: open Venus on your phone over Tailscale (private, not public).
- **More PCs**: a laptop can join and take commands too.

## How it fits together

```text
 Browser / phone ──> Web (Next.js, :3000) ──> Core (FastAPI, :9000) ──> Postgres
                                               │
                                               └─ WebSocket ──> Node (the PC app)
                                                                 opens apps, "Hey Venus",
                                                                 orb + tray icon
```

| Part | Folder | What it is |
| --- | --- | --- |
| Core | `apps/core` | The brain. FastAPI + PostgreSQL. Saves chats, memories and settings, talks to OpenAI and Fish Audio, sends commands to your PCs |
| Web | `apps/web` | Next.js page at `http://localhost:3000`: chat, settings, 3D Venus |
| Node | `apps/node` | Python tray app on each PC. Runs the commands, listens for "Hey Venus", shows the orb |
| Protocol | `packages/venus-protocol` | Message formats Core and Node share |

Core, the web page and Postgres run in Docker. The Node runs straight on
your PC, because it has to open your apps and use your mic.

## What you need

- [Docker](https://www.docker.com/) (Docker Desktop on Windows, `docker` +
  `docker compose` on Linux)
- Python 3.11 or newer
- Keys (optional): [OpenAI](https://platform.openai.com/) for chat and
  [Fish Audio](https://fish.audio/) for her voice. Without keys she still
  opens apps and sites from typed commands, she just can't chat.

On Linux the PC part also needs a few system packages:

```bash
# Arch / CachyOS
sudo pacman -S --needed docker docker-compose python tk portaudio libnotify
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # then log out and back in

# Debian / Ubuntu
sudo apt install docker.io docker-compose-plugin python3-venv python3-tk libportaudio2 libnotify-bin
```

## Install

### Windows

```powershell
git clone https://github.com/Umrkimy/Venus.git
cd Venus
.\setup-venus.cmd
```

Or just double-click `setup-venus.cmd`.

### Linux

```bash
git clone https://github.com/Umrkimy/Venus.git
cd Venus
./setup-venus.sh
```

Both do the same thing:

1. check Docker and Python,
2. write `.env`, `apps/core/.env` and `apps/node/.env` with fresh random
   secrets (if a file already exists it's kept, so running it again is safe),
3. install the PC part into `apps/node/.venv`,
4. download the "Hey Venus" speech model (about 40 MB),
5. build and start Venus in Docker (the first build takes a few minutes),
6. ask you for a username and password.

Then open `http://localhost:3000`, sign in, and put your keys in
**Settings, AI model** and **Settings, Voice**. They're saved encrypted in
the database.

## Everyday use

| | Windows | Linux |
| --- | --- | --- |
| Start Venus | double-click `start-venus-use.cmd` | `./start-venus.sh --use` |
| Start with the PC | tray menu, Start with Windows | tray menu, Start at login |
| Quit the PC part | tray menu, Quit | tray menu, Quit |

Postgres, Core and the web page restart by themselves if they crash and come
back after a reboot once Docker is running. The tray icon is the PC part:
right-click it for Open Venus, Mute mic, Stop talking, start at login and
Quit. Grey dot = not connected or muted, red = listening for "Hey Venus".

After pulling new code, run the start command again. It rebuilds.

## Settings files

The setup writes these. The `.env.example` next to each one explains every
value. Don't commit `.env` files.

| File | What's in it |
| --- | --- |
| `.env` | Postgres password, backup folder, your own domain |
| `apps/core/.env` | Node token, database address, encryption key, fallback keys |
| `apps/node/.env` | This PC's name, its token, wake phrases, projects folder, mic |

Things you'll probably change in `apps/node/.env`:

```ini
# Folder with your code projects, for "open project X"
VENUS_NODE_PROJECTS_ROOT=D:/Projects        # or /home/you/projects on Linux
# What wakes her up (lowercase, comma-separated)
VENUS_NODE_WAKE_PHRASES=hey venus,venus
# Part of your mic's name. Empty = default mic. Also in Settings, General.
VENUS_NODE_MIC=Realtek
```

Quit the tray app and start Venus again after changing it.

## Use Venus on your phone

[Tailscale](https://tailscale.com) is a free private network between your
own devices. Only devices signed in to your Tailscale account can open
Venus, nothing is on the public internet. You get HTTPS, so the phone's mic
works too.

1. Install Tailscale on the PC and the phone, same account.
2. In the Tailscale admin console, DNS page: turn on MagicDNS and HTTPS
   Certificates.
3. With Venus running:

```powershell
.\scripts\phone-access.ps1          # Windows
```

```bash
./scripts/phone-access.sh           # Linux
```

It prints something like `https://my-pc.tailnet-name.ts.net`. Open that on
your phone with Tailscale connected and log in. It stays on after a reboot.
`-Off` (Windows) or `--off` (Linux) stops it.

On Linux, if `tailscale serve` says access denied, run
`sudo tailscale set --operator=$USER` once.

### Your own domain (optional)

Instead of the `ts.net` name you can use a domain you own, like
`https://venus.example.com`. Still private: the domain points at the PC's
Tailscale address, which only your devices can reach.
[Caddy](https://caddyserver.com) answers there (about 45 MB of RAM) and gets
a free certificate through your DNS. These steps assume your DNS is on
Cloudflare.

1. Set up Tailscale as above. `tailscale ip -4` shows the PC's address
   (starts with `100.`).
2. In Cloudflare add an `A` record (for example `venus`) to that address,
   proxy off ("DNS only", grey cloud).
3. Make a Cloudflare API token with the "Edit zone DNS" template, only for
   that domain.
4. In the root `.env` set `VENUS_DOMAIN=venus.example.com` and
   `CLOUDFLARE_API_TOKEN=...`.
5. Run `.\scripts\domain-access.ps1` (Windows) or
   `./scripts/domain-access.sh` (Linux).

It downloads Caddy into `tools/caddy` (asks first), stops the `ts.net` share
and restarts the tray app, which keeps Caddy running from then on. Caddy's
log is `apps/node/data/caddy.log`. To go back: empty `VENUS_DOMAIN`, restart
Venus, run phone-access again.

## Another PC

A second PC (a laptop, say) can run just the Node and take commands from
the same Venus. It reaches Core over Tailscale.

1. On the main PC, set up phone access or your own domain (above). Both
   print the address for other PCs, like
   `wss://venus.example.com:9443/nodes/connect`.
2. On the main PC: Settings, Devices, Add device. Copy the token (it's only
   shown once).
3. On the other PC: install Tailscale (same account) and Python 3.11+, clone
   Venus and run `setup-venus-node.cmd` (Windows) or
   `./setup-venus.sh --node-only` (Linux). Give it the address and the token.
   No Docker needed there.

Once two PCs are online the chat shows a PC picker next to the send button.
"Hey Venus" only runs on the main PC for now.

## Devices and logins

Settings, Devices shows every PC with its own token and when it was last
seen. Revoke cuts one off right away.

- The main PC's token (from setup) shows up as "Main PC". It can't be revoked
  from the web, so someone with a stolen phone login can't lock you out of
  your own PC. To change it, edit it in both `apps/core/.env` and
  `apps/node/.env` and restart.
- A token is locked to the first PC that uses it, so a copied token can't
  pretend to be another PC.
- Core only keeps a hash of each token.

The same page lists every browser that's signed in. Sign out one, or "Sign
out all other browsers" if you lose your phone. Logins expire after 30 days.

## Backups

A `backup` container saves the database once at start and then every day.
It keeps the newest 7 daily and 4 weekly files in `./backups`, or wherever
`VENUS_BACKUP_DIR` in the root `.env` points (another drive is better).

Restoring (try it on a throwaway database first):

```powershell
.\scripts\restore-db.ps1 -File backups\daily\venus-2026-10-06.dump -Target venus_restore_test
```

```bash
./scripts/restore-db.sh backups/daily/venus-2026-10-06.dump venus_restore_test
```

Without a target it replaces the real database. It asks you to type
`RESTORE` and saves the current one as `pre-restore-<time>.dump` first.

## Troubleshooting

- **Port 5432, 9000 or 3000 in use**: something else is on it, or dev mode
  and server mode are both running. Stop one.
- **Windows: ports blocked after a reboot**: Windows reserves random port
  ranges at boot. Quit Docker Desktop and the tray app, then in an admin
  terminal run once:
  `powershell -ExecutionPolicy Bypass -File "<your Venus folder>\scripts\reserve-ports.ps1"`
- **"password authentication failed"**: the database was made with an older
  password than the one in `.env`. Put the old one back, or wipe everything
  with `docker compose down -v` (deletes all Venus data) and run setup again.
- **Tray app does nothing**: check `apps/node/data/venus-node.log` (and
  `data/startup.log` on Linux).
- **Linux: no tray icon**: KDE shows it out of the box. GNOME needs the
  "AppIndicator and KStatusNotifierItem Support" extension.
- **Linux: "No desktop found"**: the tray app needs a desktop session. For a
  PC without one, run just the connection:
  `apps/node/.venv/bin/python -m venus_node.dev_connect`.
- **Mic in the browser doesn't work**: browsers only allow it on `localhost`
  or HTTPS (use phone access).
- **Never** use Docker Desktop's "Reset to factory defaults". It deletes the
  database. Restore a backup if it happens.

## Security

Venus can open things on your PC, so I tried to lock it down:

- Core, the web page and Postgres only listen on `127.0.0.1`. Other devices
  only get in through Tailscale.
- Passwords are hashed (Argon2). Login tries are rate limited.
- Session cookies are `HttpOnly` and `SameSite=Lax`, and `Secure` over HTTPS.
- Core refuses changes sent by another website's page (it checks the
  browser's `Sec-Fetch-Site` header), so a random site can't press buttons
  in your Venus for you.
- API keys you save in Settings are encrypted (`VENUS_CORE_SECRET_KEY`) and
  never sent back to the page.
- Every PC has its own token, stored only as a hash, and can be revoked.
- The Node checks every command again on its own: only apps from your menu,
  only `http`/`https` links, only folders inside your projects folder. No
  shell commands, ever.
- Core refuses to start with the example tokens from `.env.example`.
- The web page sends security headers (no framing, no sniffing, mic only for
  this site).

Found a security problem? Please don't open a public issue, see
[SECURITY.md](SECURITY.md).

## Developing

For changing the code: Core and the web page run from source with
auto-reload, Postgres stays in Docker. You also need
[Node.js 22+](https://nodejs.org/). One-time setup after the normal setup:

```powershell
# Windows
cd apps/core;  py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt
.\.venv\Scripts\python.exe -m alembic upgrade head
cd ../node;  .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
cd ../web;   npm ci
```

```bash
# Linux
cd apps/core && python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/python -m alembic upgrade head
cd ../node && .venv/bin/pip install -r requirements-dev.txt
cd ../web && npm ci
```

Then `start-venus.cmd` (Windows, opens Core, Node, web and the listener as
Windows Terminal tabs) or `./start-venus.sh` (Linux, all in one terminal,
Ctrl+C stops everything). Quit the tray app first, it can't run next to the
dev Node. After pulling new migrations run `alembic upgrade head` in
`apps/core` (server mode does that by itself).

### Tests

```bash
cd apps/core && .venv/bin/python -m pytest      # Core (SQLite in memory)
cd apps/node && .venv/bin/python -m pytest      # Node
apps/node/.venv/bin/python -m pytest packages/venus-protocol/tests
cd apps/web && npx tsc --noEmit && npm run lint # Web
```

(On Windows it's `.venv\Scripts\python.exe` instead of `.venv/bin/python`.)

CI runs all of that on Windows and Linux, Core again on real Postgres, builds
the Docker images and tests a backup restore. To run Core's tests on Postgres
locally, make a scratch database whose name ends in `_test` (the tests wipe
its tables) and set `VENUS_CORE_TEST_DATABASE_URL` to it.

## Portfolio demo

There's a small version of Venus for my portfolio: the real web page, but
with a pretend Core that lives in the browser. No server, no AI, no keys,
nothing touches a PC. She answers a few scripted lines, the Approve buttons
work, links really open in a new tab, and everything else resets when you
close the tab.

```bash
cd apps/web
npm run build:demo     # plain files in apps/web/out
```

Put `out/` on any static host. On Cloudflare Pages or Vercel: root
`apps/web`, build command `npm run build:demo`, output `out`. Build it on
Linux (the host or CI does): a Windows build names some prefetch files
wrong, which only makes page switches a bit slower.

The pretend Core is `apps/web/features/demo/fake-core.ts` and her lines
are in `features/demo/script.ts`.

## Credits

- 3D model support: [@pixiv/three-vrm](https://github.com/pixiv/three-vrm)
- Wake word: [Vosk](https://alphacephei.com/vosk/)
- Voice: [Fish Audio](https://fish.audio/)
- UI parts: [shadcn/ui](https://ui.shadcn.com/)
