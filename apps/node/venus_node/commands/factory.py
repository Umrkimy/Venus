from pathlib import Path

from venus_node.config import load_settings
from venus_node.commands import pc
from venus_node.commands.executor import NodeExecutor
from venus_node.commands.home import create_home_executor
from venus_node.commands.launcher import (
    create_application_command_executor,
    create_command_router,
    create_url_command_executor,
    create_project_command_executor,
)
from venus_node.storage.repositories.command_records import CommandRecordRepository


def create_node_executor(
    env_file: Path,
    database_path: Path,
) -> NodeExecutor:
    settings = load_settings(env_file)
    command_records = CommandRecordRepository(database_path)
    # pc.* looked up at call time, so Windows and Linux pick their own way.
    command_executor = create_command_router(
        open_app=create_application_command_executor(
            settings=settings,
            launch_app=lambda app_id: pc.launch_app(app_id),
            list_apps=lambda: pc.list_apps(),
        ),
        open_url=create_url_command_executor(start_target=lambda url: pc.open_link(url)),
        open_project=create_project_command_executor(
            projects_root=settings.projects_root,
            open_folder=lambda folder: pc.open_folder(folder),
        ),
        home=create_home_executor(),
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
