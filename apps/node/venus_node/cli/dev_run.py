from pathlib import Path
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from venus_node.config import load_settings
from venus_node.commands.factory import create_node_executor
from venus_protocol.schemas.commands import CommandResult


def run_spotify(
    env_file: Path,
    database_path: Path,
) -> CommandResult:
    settings = load_settings(env_file)
    executor = create_node_executor(
        env_file=env_file,
        database_path=database_path,
    )
    payload = {
        "command_id": str(uuid4()),
        "device_id": settings.device_id,
        "application_id": "spotify",
        "expires_at": datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
        + timedelta(minutes=5),
    }

    result = executor.execute_payload(payload)

    if result is None:
        raise RuntimeError("Node discarded its own local command")

    return result


def main() -> None:
    node_directory = Path(__file__).resolve().parent.parent.parent
    database_path = node_directory / "data" / "node.db"
    database_path.parent.mkdir(parents=True, exist_ok=True)

    result = run_spotify(
        env_file=node_directory / ".env",
        database_path=database_path,
    )

    print(result.model_dump_json())


if __name__ == "__main__":
    main()
