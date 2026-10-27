import os
import subprocess
import sys
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from threading import Lock
from urllib.parse import urlsplit

# The Venus server (Postgres, Core, web) runs in Docker on the main PC.
# The tray starts it, so one click on the Venus icon is enough.
STARTING = "starting"
READY = "ready"
PROBLEM = "problem"
LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}
DOCKER_DESKTOP = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Docker" / "Docker" / "Docker Desktop.exe"
CREATE_NO_WINDOW = 0x08000000


def health_url(core_url: str) -> str:
    # ws://127.0.0.1:9000/nodes/connect -> http://127.0.0.1:9000/health
    parts = urlsplit(core_url)
    scheme = "https" if parts.scheme == "wss" else "http"
    return f"{scheme}://{parts.netloc}/health"


def runs_here(core_url: str, repo_root: Path, which: Callable[[str], str | None]) -> bool:
    """Only the PC with the server on it starts it; extra PCs just connect."""
    return (
        urlsplit(core_url).hostname in LOCAL_HOSTS
        and (repo_root / "compose.yaml").is_file()
        and (repo_root / "apps" / "core" / ".env").is_file()
        and which("docker") is not None
    )


def core_answers(url: str) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            return response.status == 200
    except OSError:
        return False


def run_hidden(args: list[str], timeout: float) -> int:
    # No console window flashing up from a tray app.
    flags = CREATE_NO_WINDOW if sys.platform == "win32" else 0
    try:
        done = subprocess.run(args, capture_output=True, text=True, timeout=timeout, creationflags=flags)
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"{' '.join(args[:3])}: {exc}")
        return 1
    # "docker info" fails on purpose while Docker Desktop starts: no need to log each try.
    if done.returncode != 0 and args[:2] != ["docker", "info"]:
        print(f"{' '.join(args[:3])} failed: {(done.stderr or done.stdout).strip()[-500:]}")
    return done.returncode


def open_docker_desktop() -> None:
    if sys.platform == "win32" and DOCKER_DESKTOP.is_file():
        subprocess.Popen([str(DOCKER_DESKTOP)], creationflags=CREATE_NO_WINDOW)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", "-a", "Docker"])
    # Linux: Docker usually runs as a service already.


class Server:
    """Starts Docker and the Venus containers, and says how it went.

    Runs on its own thread; the tray reads `state` and `detail` for its menu.
    """

    def __init__(
        self,
        repo_root: Path,
        core_url: str,
        on_change: Callable[[], None] = lambda: None,
        run: Callable[[list[str], float], int] = run_hidden,
        answers: Callable[[str], bool] = core_answers,
        open_docker: Callable[[], None] = open_docker_desktop,
        sleep: Callable[[float], None] = time.sleep,
        docker_wait: float = 180,
    ) -> None:
        self._lock = Lock()
        self._state = STARTING
        self._detail = ""
        self.repo_root = repo_root
        self.health = health_url(core_url)
        self._on_change = on_change
        self._run = run
        self._answers = answers
        self._open_docker = open_docker
        self._sleep = sleep
        self.docker_wait = docker_wait

    @property
    def state(self) -> str:
        with self._lock:
            return self._state

    @property
    def detail(self) -> str:
        with self._lock:
            return self._detail

    def _set(self, state: str, detail: str = "") -> None:
        with self._lock:
            self._state, self._detail = state, detail
        self._on_change()

    def _compose(self, *args: str) -> list[str]:
        return ["docker", "compose", "--project-directory", str(self.repo_root), "--profile", "server", *args]

    def _docker_up(self) -> bool:
        return self._run(["docker", "info"], 30) == 0

    def _wait(self, check: Callable[[], bool], seconds: float) -> bool:
        waited = 0.0
        while not check():
            if waited >= seconds:
                return False
            self._sleep(3)
            waited += 3
        return True

    def start(self) -> bool:
        """True when Venus had to be started (not when it was already up)."""
        self._set(STARTING)
        # Already up: Docker kept it running, or dev mode runs Core by hand.
        if self._answers(self.health):
            self._set(READY)
            return False
        if not self._docker_up():
            print("Starting Docker Desktop.")
            self._open_docker()
            if not self._wait(self._docker_up, self.docker_wait):
                self._set(PROBLEM, "Docker didn't start. Open Docker Desktop, then Restart Venus.")
                return False
        print("Starting the Venus server.")
        if self._run(self._compose("up", "-d", "--wait"), 900) != 0:
            self._set(PROBLEM, "Venus didn't start. Try Restart Venus.")
            return False
        self._set(READY)
        return True

    def restart(self) -> None:
        self._set(STARTING)
        print("Restarting the Venus server.")
        if not self._docker_up():
            self.start()
            return
        # Fresh Core and web containers; the database and its data stay as they are.
        if self._run(self._compose("up", "-d", "--wait", "--force-recreate", "core", "web"), 900) != 0:
            self._set(PROBLEM, "Venus didn't restart. Open Docker Desktop to see why.")
            return
        self._set(READY)
