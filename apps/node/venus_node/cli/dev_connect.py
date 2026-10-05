import asyncio
from collections.abc import Callable
from pathlib import Path

from venus_node.config import NodeSettings, load_settings
from venus_node.commands.factory import (
    create_fake_node_executor,
    create_node_executor,
)
from venus_node.commands.projects import list_projects
from venus_node.commands.start_apps import StartApp, read_start_apps, run_powershell
from venus_node.connection.client import keep_connected
from venus_protocol.schemas.connections import NodeHello


def run_connect(
    env_file: Path,
    on_connected: Callable[[NodeHello], None] | None = None,
    on_retry: Callable[[], None] | None = None,
) -> None:
    settings = load_settings(env_file)
    database_path = env_file.parent / "data" / "node.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.real_actions:
        print("Real actions enabled: approved commands will open apps")
        executor = create_node_executor(env_file, database_path)
    else:
        executor = create_fake_node_executor(env_file, database_path)

    asyncio.run(
        keep_connected(
            settings,
            on_connected=on_connected or print_connected,
            on_retry=on_retry or print_retry,
            execute_payload=executor.execute_payload,
            list_apps=list_reported_apps,
            list_projects=lambda: list_reported_projects(settings),
        ),
    )


def print_connected(hello: NodeHello) -> None:
    print(f"Core confirmed Node: {hello.device_id}")


def print_retry() -> None:
    print("Core unavailable; retrying in 1 second")


def list_reported_apps() -> list[StartApp]:
    return read_start_apps(run_powershell)


def list_reported_projects(settings: NodeSettings) -> list[str]:
    if settings.projects_root is None:
        return []
    return list_projects(settings.projects_root)


def main() -> None:
    from venus_node.app.single import CONNECTION, already_running_message, claim

    if not claim(CONNECTION):
        print(already_running_message("Connection"))
        return
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_connect(node_directory / ".env")


if __name__ == "__main__":
    main()
