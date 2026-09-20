import asyncio
from pathlib import Path

from venus_node.config import load_settings
from venus_node.core_connection import keep_connected
from venus_protocol.schemas.connections import NodeHello


def run_connect(env_file: Path) -> None:
    settings = load_settings(env_file)
    asyncio.run(
        keep_connected(
            settings,
            on_connected=print_connected,
            on_retry=print_retry,
        ),
    )


def print_connected(hello: NodeHello) -> None:
    print(f"Core confirmed Node: {hello.device_id}")


def print_retry() -> None:
    print("Core unavailable; retrying in 1 second")


def main():
    node_directory = Path(__file__).resolve().parent.parent
    run_connect(node_directory / ".env")


if __name__ == "__main__":
    main()
