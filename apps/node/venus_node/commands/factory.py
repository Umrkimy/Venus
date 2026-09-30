from pathlib import Path

from venus_node.config import load_settings
from venus_node.commands.executor import NodeExecutor
from venus_node.commands.launcher import (
    create_application_command_executor,
    start_windows_target,
    create_command_router,
    create_url_command_executor,
    create_project_command_executor,
    open_in_vscode,
)
from venus_node.commands.start_apps import read_start_apps, run_powershell
from venus_node.storage.repositories.command_records import CommandRecordRepository


def create_node_executor(
    env_file: Path,
    database_path: Path,
) -> NodeExecutor:
    settings = load_settings(env_file)
    command_records = CommandRecordRepository(database_path)
    command_executor = create_command_router(
        open_app=create_application_command_executor(
            settings=settings,
            start_target=start_windows_target,
            list_apps=lambda: read_start_apps(run_powershell),
        ),
        open_url=create_url_command_executor(start_target=start_windows_target),
        open_project=create_project_command_executor(
            projects_root=settings.projects_root,
            open_folder=open_in_vscode,
        ),
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

    # Keep WebSocket commands fake; only real executors open apps.
    return NodeExecutor(
        device_id=settings.device_id,
        command_records=command_records,
    )
