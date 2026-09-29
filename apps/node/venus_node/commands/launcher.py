import os
from collections.abc import Callable

from venus_node.commands.start_apps import StartApp
from venus_node.config import NodeSettings
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand


def start_windows_target(target: str) -> None:
    os.startfile(target)


def create_application_command_executor(
    settings: NodeSettings,
    start_target: Callable[[str], None],
    list_apps: Callable[[], list[StartApp]],
) -> Callable[[OpenApplicationCommand], CommandResult]:
    def execute(command: OpenApplicationCommand) -> CommandResult:
        # Temporary: the web sends "spotify" until the app picker replaces it
        if command.application_id == "spotify":
            start_target(settings.spotify_target)
            return CommandResult(
                command_id=command.command_id,
                status="succeeded",
                detail="Launch requested",
            )

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