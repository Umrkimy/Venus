from pathlib import Path

from venus_node.config import load_settings
from venus_node.executor import NodeExecutor
from venus_node.launcher import (
    create_spotify_command_executor,
    start_windows_target,
)
from venus_node.repositories.command_records import CommandRecordRepository


def create_node_executor(
    env_file: Path,
    database_path: Path,
) -> NodeExecutor:
    settings = load_settings(env_file)
    command_records = CommandRecordRepository(database_path)
    command_executor = create_spotify_command_executor(
        settings=settings,
        start_target=start_windows_target,
    )

    return NodeExecutor(
        device_id=settings.device_id,
        command_records=command_records,
        command_executor=command_executor,
    )


def create_fake_node_executor(
    env_file: Path,
    database_path: Path,
) -> NodeExecutor:
    settings = load_settings(env_file)
    command_records = CommandRecordRepository(database_path)

    # Keep WebSocket commands fake; only dev_run can open Spotify.
    return NodeExecutor(
        device_id=settings.device_id,
        command_records=command_records,
    )
