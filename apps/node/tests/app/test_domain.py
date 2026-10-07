import threading
from pathlib import Path

from venus_node.app import domain


def make_root(tmp_path: Path, env: str, caddy: bool = True) -> Path:
    (tmp_path / ".env").write_text(env, encoding="utf-8")
    if caddy:
        (tmp_path / "tools" / "caddy").mkdir(parents=True)
        (tmp_path / "tools" / "caddy" / "caddy.exe").write_bytes(b"")
    return tmp_path


def test_caddy_command_runs_the_caddyfile_with_the_root_env_file(tmp_path):
    root = make_root(tmp_path, "VENUS_DOMAIN=venus.example.com\n")

    command = domain.caddy_command(root)

    assert command == [
        str(root / "tools" / "caddy" / "caddy.exe"),
        "run",
        "--config",
        str(root / "scripts" / "domain" / "Caddyfile"),
        "--adapter",
        "caddyfile",
        "--envfile",
        str(root / ".env"),
    ]


def test_no_caddy_without_a_domain(tmp_path):
    root = make_root(tmp_path, "VENUS_DOMAIN=\nCLOUDFLARE_API_TOKEN=x\n")

    assert domain.caddy_command(root) is None


def test_no_caddy_when_it_is_not_downloaded(tmp_path):
    root = make_root(tmp_path, "VENUS_DOMAIN=venus.example.com\n", caddy=False)

    assert domain.caddy_command(root) is None


class FakeProcess:
    def __init__(self, exit_code: int | None = None):
        self.exit_code = exit_code
        self.exited = threading.Event()
        self.terminated = False

    def wait(self):
        if self.exit_code is None:
            self.exited.wait(5)  # Runs until stop() terminates it.
        return self.exit_code

    def poll(self):
        return self.exit_code

    def terminate(self):
        self.terminated = True
        self.exit_code = 1
        self.exited.set()


def test_caddy_gets_the_tailnet_address_and_no_window(tmp_path):
    started = []

    def popen(command, **options):
        started.append((command, options))
        return FakeProcess(exit_code=0)

    proxy = domain.DomainProxy(["caddy.exe", "run"], tmp_path / "caddy.log", lambda: "100.64.0.1", popen)

    with open(tmp_path / "caddy.log", "w") as log:
        assert proxy.run_once(log) == "exit code 0"

    command, options = started[0]
    assert command == ["caddy.exe", "run"]
    assert options["env"]["VENUS_TAILNET_IP"] == "100.64.0.1"
    assert options["creationflags"] == domain.CREATE_NO_WINDOW


def test_caddy_waits_while_tailscale_has_no_address(tmp_path):
    started = []
    proxy = domain.DomainProxy(["caddy.exe"], tmp_path / "caddy.log", lambda: None, lambda *a, **k: started.append(a))

    with open(tmp_path / "caddy.log", "w") as log:
        assert proxy.run_once(log) == "no Tailscale address yet"

    assert started == []


def test_stop_ends_the_running_caddy_and_the_retry_loop(tmp_path):
    process = FakeProcess()
    proxy = domain.DomainProxy(["caddy.exe"], tmp_path / "caddy.log", lambda: "100.64.0.1", lambda *a, **k: process)
    loop = threading.Thread(target=proxy.run)
    loop.start()
    while proxy.process is None:
        loop.join(0.01)

    proxy.stop()
    loop.join(5)

    assert process.terminated is True
    assert not loop.is_alive()


def test_crashed_caddy_is_started_again(tmp_path, monkeypatch):
    monkeypatch.setattr(domain, "RETRY_SECONDS", 0)
    processes = []

    def popen(command, **options):
        processes.append(FakeProcess(exit_code=1))
        if len(processes) == 2:
            proxy.stopped.set()
        return processes[-1]

    proxy = domain.DomainProxy(["caddy.exe"], tmp_path / "caddy.log", lambda: "100.64.0.1", popen)
    proxy.run()

    assert len(processes) == 2
