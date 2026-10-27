# Install and settings

Step by step, for people who haven't set up something like this before.
It takes about 15 minutes, most of it waiting for downloads.

Works on **Windows 10/11**, **macOS** and **Linux**. (The Mac version is new:
if something doesn't work there, please open an issue.)

## 1. Install what Venus needs

**Windows**

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/).
   Install it, open it once, and wait until it says "Engine running".
   Docker is what runs Venus's server, database and web page in the
   background.
2. [Python](https://www.python.org/downloads/) 3.11 or newer. In the
   installer, tick **"Add python.exe to PATH"** before clicking Install.
   Python runs the small app on your PC that opens things and listens for
   "Hey Venus".
3. Optional: [Git](https://git-scm.com/downloads), to download Venus and get
   updates easily. You can also download it as a ZIP instead (below).

**macOS**

1. [Docker Desktop](https://www.docker.com/products/docker-desktop/) (pick
   Apple chip or Intel to match your Mac). Open it once and wait until it's
   running.
2. [Python](https://www.python.org/downloads/) 3.11 or newer from
   python.org (it includes what the orb window needs). With Homebrew instead:
   `brew install python python-tk`.
3. Git comes with Apple's developer tools: type `git` in Terminal and macOS
   offers to install them. Or use the ZIP (below).

**Linux**

```bash
# Arch / CachyOS
sudo pacman -S --needed git docker docker-compose python tk portaudio libnotify
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # then log out and back in

# Debian / Ubuntu
sudo apt install git docker.io docker-compose-plugin python3-venv python3-tk libportaudio2 libnotify-bin
```

## 2. Download Venus

With Git (Windows: open **PowerShell**; Mac and Linux: **Terminal**):

```bash
git clone https://github.com/Umrkimy/Venus.git
cd Venus
```

Without Git: on the GitHub page click the green **Code** button, then
**Download ZIP**, and unzip it somewhere like `Documents\Venus`.

## 3. Run the setup

**Windows:** open the Venus folder and double-click `setup-venus.cmd`.
**Mac and Linux:** in Terminal, in the Venus folder, run `./setup-venus.sh`.

Make sure Docker is running first. The setup:

1. checks that Docker and Python are there,
2. makes your settings files (`.env`) with fresh random passwords and keys,
   so you **don't need to fill them in yourself**,
3. asks for the folder with your code projects (for "open project X"). Just
   press Enter if you don't have one,
4. installs the PC app and downloads the "Hey Venus" speech model (about
   40 MB),
5. builds and starts Venus (the first time takes a few minutes),
6. asks you to pick a **username and password** for the web page (12+
   characters).

Running it again is safe: it keeps the settings files that already exist.

## 4. Sign in and add your keys

Open <http://localhost:3000> and sign in. Venus already opens apps and
sites from typed commands. For chatting and her voice she needs keys
(you pay those services yourself, usually a few dollars a month):

- **Settings, AI model**: an [OpenAI API key](https://platform.openai.com/api-keys)
  (this is separate from a ChatGPT subscription; add a few dollars of credit).
- **Settings, Voice**: a [Fish Audio](https://fish.audio/) API key for her voice.

Keys you save there are stored encrypted. Settings, Usage shows what each
chat cost.

## 5. Check your settings files

The setup filled in everything that has to be there, so Venus works
without touching these. Look at them once anyway, in case you want to
change something. Open them with Notepad (Windows) or any text editor.
Files starting with a dot can be hidden: in File Explorer turn on View,
Show, Hidden items.

| File | What's in it | Change it? |
| --- | --- | --- |
| `apps/node/.env` | This PC: its name, wake phrases, projects folder, mic | Yes, if you like (below) |
| `.env` | Database password, backup folder, your own domain | Only the backup folder or domain |
| `apps/core/.env` | Secret keys and the PC token | **No.** Changing these breaks sign-in or the saved keys |

Things you might change in `apps/node/.env`:

```ini
# Folder with your code projects, for "open project X". Empty = off.
VENUS_NODE_PROJECTS_ROOT=D:/Projects        # or /home/you/projects on Linux
# What wakes her up (lowercase, comma-separated)
VENUS_NODE_WAKE_PHRASES=hey venus,venus
# Part of your mic's name. Empty = default mic. Also in Settings, General.
VENUS_NODE_MIC=Realtek
```

Use forward slashes `/` in folder paths. After saving, quit the tray icon
(right-click, Quit) and start Venus again (next step). Every value is
explained in the `.env.example` file next to each `.env`. Never share or
upload your `.env` files: they hold your passwords.

## Everyday use

| | Windows | Mac and Linux |
| --- | --- | --- |
| Start Venus | the **Venus** icon (desktop or Start menu) | `./start-venus.sh --use` |
| Start with the PC | tray menu, Start with Windows | tray menu, Start at login |
| Quit the PC part | tray menu, Quit | tray menu, Quit |

**On a Mac** the Venus dot sits in the menu bar at the top. The first time,
macOS asks a few things; say yes, or Venus can't do that part:

- **Microphone** (for "Hey Venus"): System Settings, Privacy & Security,
  Microphone, turn on Terminal (or Python).
- **Notifications** (calendar reminders): allow them for Script Editor.
- `lock my pc` turns the screen off, which locks the Mac when "Require
  password after screen saver begins or display is turned off" is on
  (System Settings, Lock Screen).

The Venus icon starts Docker Desktop if it's closed, then the server, and
says "Venus is ready" when you can use it (clicking it again opens Venus). Lost
the icon? In `apps\node`, run `.venv\Scripts\python.exe -m venus_node.app.shortcut`.
The server parts restart by themselves if they crash. The tray icon is the PC
part: right-click it for Open Venus, Restart Venus, Mute mic, Stop talking,
start at login and Quit. On an extra PC (Core somewhere else) it only connects;
`VENUS_NODE_START_SERVER=false` in `apps/node/.env` turns the starting off. Grey dot =
not connected or muted, red = listening for "Hey Venus".

**Updating:** with Git, `git pull`, then run the start command again (it
rebuilds). With a ZIP: unzip the new version, copy your three `.env` files
into the same places in the new folder, and run the setup again.

Something not working? See [troubleshooting](backups-and-troubleshooting.md#troubleshooting).

[Back to the README](../README.md)
