import json
import subprocess
from collections.abc import Callable
from dataclasses import dataclass

START_APPS_SCRIPT = (
    "[Console]::OutputEncoding = [Text.Encoding]::UTF8; "
    "Get-StartApps | ConvertTo-Json -Compress"
)


@dataclass(frozen=True)
class StartApp:
    name: str
    app_id: str


def parse_start_apps(raw_json: str) -> list[StartApp]:
    if not raw_json.strip():
        return []

    data = json.loads(raw_json)
    # PowerShell prints one object, not a list, when there is only one app
    if isinstance(data, dict):
        data = [data]

    return [
        StartApp(name=item["Name"], app_id=item["AppID"])
        for item in data
        if item.get("AppID")
    ]


def run_powershell(script: str) -> str:
    completed = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        timeout=15,
        # The tray app has no console, so Windows would open a new
        # PowerShell window on every "open ..." command.
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    return completed.stdout


def read_start_apps(run: Callable[[str], str]) -> list[StartApp]:
    return parse_start_apps(run(START_APPS_SCRIPT))