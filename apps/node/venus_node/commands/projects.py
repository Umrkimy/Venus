from pathlib import Path


def list_projects(root: Path) -> list[str]:
    # Direct subfolders only; hidden ones like .git are not projects
    return sorted(
        entry.name
        for entry in root.iterdir()
        if entry.is_dir() and not entry.name.startswith(".")
    )
