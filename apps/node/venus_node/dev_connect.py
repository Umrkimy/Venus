import asyncio
from pathlib import Path

from venus_node.config import load_settings
from venus_node.core_connection import connect_to_core
from venus_protocol.schemas.connections import NodeHello


def run_connect(env_file: Path) -> NodeHello:
    settings = load_settings(env_file)
    return asyncio.run(connect_to_core(settings))


def main():
    node_directory = Path(__file__).resolve().parent.parent
    confirmed_hello = run_connect(node_directory / ".env")

    print(f"Core confirmed Node: {confirmed_hello.device_id}")


if __name__ == "__main__":
    main()