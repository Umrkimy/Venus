from pathlib import Path

from venus_node.commands.projects import list_projects


def test_list_projects_returns_direct_subfolders_only(tmp_path: Path):
    (tmp_path / "Venus" / "apps").mkdir(parents=True)
    (tmp_path / "notes.txt").write_text("not a project")

    assert list_projects(tmp_path) == ["Venus"]


def test_list_projects_skips_hidden_folders(tmp_path: Path):
    (tmp_path / "Venus").mkdir()
    (tmp_path / ".git").mkdir()

    assert list_projects(tmp_path) == ["Venus"]
