import asyncio
from pathlib import Path

from venus_node.config import load_settings
from venus_node.commands.factory import create_fake_node_executor
from venus_node.connection.client import keep_connected
from venus_protocol.schemas.connections import NodeHello


def run_connect(env_file: Path) -> None:
    settings = load_settings(env_file)
    database_path = env_file.parent / "data" / "node.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)
    executor = create_fake_node_executor(env_file, database_path)

    asyncio.run(
        keep_connected(
            settings,
            on_connected=print_connected,
            on_retry=print_retry,
            execute_payload=executor.execute_payload,
        ),
    )


def print_connected(hello: NodeHello) -> None:
    print(f"Core confirmed Node: {hello.device_id}")


def print_retry() -> None:
    print("Core unavailable; retrying in 1 second")


def main() -> None:
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_connect(node_directory / ".env")


if __name__ == "__main__":
    main()
