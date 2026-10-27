from venus_node.app.server import PROBLEM, READY, STARTING, Server, health_url, runs_here


class FakeDocker:
    """Docker and Core as the tray sees them: commands in, exit codes out."""

    def __init__(self, docker_up=True, core_up=False, up_works=True, docker_starts_after=None):
        self.docker_up = docker_up
        self.core_up = core_up
        self.up_works = up_works
        self.docker_starts_after = docker_starts_after
        self.commands = []
        self.opened_desktop = 0
        self.slept = 0.0

    def run(self, args, timeout):
        self.commands.append(args)
        if args == ["docker", "info"]:
            return 0 if self.docker_up else 1
        if "up" in args:
            if self.up_works:
                self.core_up = True
                return 0
            return 1
        return 0

    def open_docker(self):
        self.opened_desktop += 1

    def sleep(self, seconds):
        self.slept += seconds
        if self.docker_starts_after is not None and self.slept >= self.docker_starts_after:
            self.docker_up = True


def build(fake, tmp_path):
    changes = []
    holder = {}
    server = Server(
        tmp_path,
        "ws://127.0.0.1:9000/nodes/connect",
        on_change=lambda: changes.append(holder["server"].state),
        run=fake.run,
        answers=lambda url: fake.core_up,
        open_docker=fake.open_docker,
        sleep=fake.sleep,
        docker_wait=30,
    )
    holder["server"] = server
    return server, changes


def test_health_url_from_the_node_connection():
    assert health_url("ws://127.0.0.1:9000/nodes/connect") == "http://127.0.0.1:9000/health"
    assert health_url("wss://venus.example.com:9443/nodes/connect") == "https://venus.example.com:9443/health"


def test_runs_here_only_on_the_pc_with_the_server(tmp_path):
    (tmp_path / "apps" / "core").mkdir(parents=True)
    (tmp_path / "compose.yaml").write_text("services: {}\n")
    (tmp_path / "apps" / "core" / ".env").write_text("")
    docker = lambda name: "docker.exe"  # noqa: E731

    assert runs_here("ws://127.0.0.1:9000/nodes/connect", tmp_path, docker) is True
    assert runs_here("ws://localhost:9000/nodes/connect", tmp_path, docker) is True
    # Another PC connecting over the network never starts Docker.
    assert runs_here("wss://venus.example.com:9443/nodes/connect", tmp_path, docker) is False
    assert runs_here("ws://127.0.0.1:9000/nodes/connect", tmp_path, lambda name: None) is False
    assert runs_here("ws://127.0.0.1:9000/nodes/connect", tmp_path / "elsewhere", docker) is False


def test_already_running_venus_is_left_alone(tmp_path):
    fake = FakeDocker(core_up=True)
    server, changes = build(fake, tmp_path)

    assert server.start() is False

    assert server.state == READY
    assert fake.commands == []
    assert changes == [STARTING, READY]


def test_starts_the_containers_when_docker_is_up(tmp_path):
    fake = FakeDocker()
    server, _ = build(fake, tmp_path)

    assert server.start() is True

    assert server.state == READY
    assert fake.opened_desktop == 0
    up = fake.commands[-1]
    assert up[:2] == ["docker", "compose"]
    assert up[-3:] == ["up", "-d", "--wait"]
    assert ["--profile", "server"] == up[up.index("--profile"):up.index("--profile") + 2]
    assert str(tmp_path) in up


def test_opens_docker_desktop_and_waits_for_it(tmp_path):
    fake = FakeDocker(docker_up=False, docker_starts_after=9)
    server, _ = build(fake, tmp_path)

    assert server.start() is True

    assert fake.opened_desktop == 1
    assert fake.slept == 9
    assert server.state == READY


def test_docker_that_never_starts_is_a_problem(tmp_path):
    fake = FakeDocker(docker_up=False)
    server, _ = build(fake, tmp_path)

    assert server.start() is False

    assert server.state == PROBLEM
    assert "Docker didn't start" in server.detail
    assert not any("up" in command for command in fake.commands)


def test_containers_that_fail_are_a_problem(tmp_path):
    fake = FakeDocker(up_works=False)
    server, _ = build(fake, tmp_path)

    assert server.start() is False

    assert server.state == PROBLEM
    assert "Restart Venus" in server.detail


def test_restart_recreates_core_and_web_only(tmp_path):
    fake = FakeDocker(core_up=True)
    server, changes = build(fake, tmp_path)

    server.restart()

    assert server.state == READY
    command = fake.commands[-1]
    assert command[-2:] == ["core", "web"]
    assert "--force-recreate" in command
    assert "postgres" not in command
    assert changes == [STARTING, READY]


def test_restart_with_docker_off_starts_everything(tmp_path):
    fake = FakeDocker(docker_up=False, docker_starts_after=3)
    server, _ = build(fake, tmp_path)

    server.restart()

    assert fake.opened_desktop == 1
    assert server.state == READY
