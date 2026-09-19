import os
from collections.abc import Callable

from venus_node.config import NodeSettings
from venus_protocol.schemas.commands import CommandResult, OpenApplicationCommand


def launch_spotify(
    spotify_target: str,
    start_target: Callable[[str], None],
) -> None:
    start_target(spotify_target)


def start_windows_target(target: str) -> None:
    os.startfile(target)


def launch_configured_spotify(
    settings: NodeSettings,
    start_target: Callable[[str], None],
) -> None:
    launch_spotify(
        spotify_target=settings.spotify_target,
        start_target=start_target,
    )


def create_spotify_command_executor(
    settings: NodeSettings,
    start_target: Callable[[str], None],
) -> Callable[[OpenApplicationCommand], CommandResult]:
    def execute(command: OpenApplicationCommand) -> CommandResult:
        launch_configured_spotify(
            settings=settings,
            start_target=start_target,
        )
        return CommandResult(
            command_id=command.command_id,
            status="succeeded",
            detail="Spotify launch requested",
        )

    return execute
