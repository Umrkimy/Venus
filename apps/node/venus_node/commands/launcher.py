import os
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from venus_node.commands.projects import list_projects
from venus_node.commands.start_apps import StartApp
from venus_node.config import NodeSettings
from venus_protocol.schemas.commands import (
    CommandResult,
    NodeCommand,
    OpenApplicationCommand,
    OpenProjectCommand,
    OpenUrlCommand,
)


def start_windows_target(target: str) -> None:
    os.startfile(target)


def open_in_vscode(folder: Path) -> None:
    code_cli = shutil.which("code")
    if code_cli is None:
        raise FileNotFoundError("VS Code not found")
    # code.cmd is a batch file; start Code.exe directly so the folder is passed safely
    code_exe = Path(code_cli).parent.parent / "Code.exe"
    subprocess.Popen([str(code_exe), str(folder)])


def create_application_command_executor(
    settings: NodeSettings,
    start_target: Callable[[str], None],
    list_apps: Callable[[], list[StartApp]],
) -> Callable[[OpenApplicationCommand], CommandResult]:
    def execute(command: OpenApplicationCommand) -> CommandResult:
        # Read the list each time so newly installed apps work right away
        listed_ids = {app.app_id for app in list_apps()}
        if command.application_id not in listed_ids:
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Not in this PC's Start menu",
            )

        start_target(f"shell:AppsFolder\\{command.application_id}")
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Launch requested",
        )

    return execute


def create_url_command_executor(
    start_target: Callable[[str], None],
) -> Callable[[OpenUrlCommand], CommandResult]:
    def execute(command: OpenUrlCommand) -> CommandResult:
        # The default browser handles http(s) links (Brave on this PC)
        start_target(str(command.url))
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Browser open requested",
        )

    return execute


def create_project_command_executor(
    projects_root: Path | None,
    open_folder: Callable[[Path], None],
) -> Callable[[OpenProjectCommand], CommandResult]:
    def execute(command: OpenProjectCommand) -> CommandResult:
        if projects_root is None:
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Projects are not set up on this PC",
            )

        # Read the folders each time so new projects work right away
        if command.project_name not in list_projects(projects_root):
            return CommandResult(
                command_id=command.command_id,
                status="denied",
                detail="Not in this PC's projects",
            )

        open_folder(projects_root / command.project_name)
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="VS Code open requested",
        )

    return execute


def create_command_router(
    open_app: Callable[[OpenApplicationCommand], CommandResult],
    open_url: Callable[[OpenUrlCommand], CommandResult],
    open_project: Callable[[OpenProjectCommand], CommandResult],
) -> Callable[[NodeCommand], CommandResult]:
    def execute(command: NodeCommand) -> CommandResult:
        if isinstance(command, OpenUrlCommand):
            return open_url(command)
        if isinstance(command, OpenProjectCommand):
            return open_project(command)
        return open_app(command)

    return execute
