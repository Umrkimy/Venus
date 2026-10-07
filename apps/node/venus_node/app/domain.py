import os
import shutil
import subprocess
import threading
from pathlib import Path
from typing import Callable

from dotenv import dotenv_values

# Your own domain (README "Your own domain"): Caddy answers https://<VENUS_DOMAIN>
# on the PC's Tailscale address and passes requests to the web app.
CREATE_NO_WINDOW = 0x08000000  # Caddy is a console program; no window popping up.
RETRY_SECONDS = 10


def caddy_command(root: Path) -> list[str] | None:
    """How to start Caddy, or None when no domain is set or Caddy isn't downloaded."""
    env_file = root / ".env"
    caddy = root / "tools" / "caddy" / "caddy.exe"
    if not dotenv_values(env_file).get("VENUS_DOMAIN") or not caddy.exists():
        return None
    caddyfile = root / "scripts" / "domain" / "Caddyfile"
    # --envfile: Caddy reads VENUS_DOMAIN and the Cloudflare token itself,
    # so the token never passes through this app.
    return [str(caddy), "run", "--config", str(caddyfile), "--adapter", "caddyfile", "--envfile", str(env_file)]


def tailnet_ip() -> str | None:
    """This PC's Tailscale address, or None while Tailscale isn't connected."""
    tailscale = shutil.which("tailscale") or os.path.join(
        os.environ.get("ProgramFiles", r"C:\Program Files"), "Tailscale", "tailscale.exe"
    )
    try:
        result = subprocess.run(
            [tailscale, "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=CREATE_NO_WINDOW,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = result.stdout.split()
    return lines[0] if result.returncode == 0 and lines else None


class DomainProxy:
    """Keeps Caddy running while the tray app runs.

    At login Tailscale may not have its address yet, and Caddy stops if it
    can't listen there, so both are retried every RETRY_SECONDS.
    """

    def __init__(
        self,
        command: list[str],
        log_path: Path,
        find_ip: Callable[[], str | None] = tailnet_ip,
        popen=subprocess.Popen,
    ) -> None:
        self.command = command
        self.log_path = log_path
        self.find_ip = find_ip
        self.popen = popen
        self.stopped = threading.Event()
        self.lock = threading.Lock()
        self.process = None

    def start(self) -> None:
        threading.Thread(target=self.run, daemon=True).start()

    def run(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "w", encoding="utf-8") as log:
            while not self.stopped.is_set():
                code = self.run_once(log)
                if self.stopped.is_set():
                    break
                print(f"Caddy not running ({code}); retrying in {RETRY_SECONDS} s. Log: {self.log_path}")
                self.stopped.wait(RETRY_SECONDS)

    def run_once(self, log) -> str:
        ip = self.find_ip()
        if ip is None:
            return "no Tailscale address yet"
        with self.lock:
            if self.stopped.is_set():
                return "stopped"
            self.process = self.popen(
                self.command,
                env={**os.environ, "VENUS_TAILNET_IP": ip},
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=CREATE_NO_WINDOW,
            )
        print(f"Caddy started on {ip}")
        return f"exit code {self.process.wait()}"

    def stop(self) -> None:
        with self.lock:
            self.stopped.set()
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()


def start_domain(root: Path, log_path: Path) -> DomainProxy | None:
    command = caddy_command(root)
    if command is None:
        return None
    proxy = DomainProxy(command, log_path)
    proxy.start()
    return proxy
