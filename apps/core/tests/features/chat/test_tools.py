import pytest

from features.chat.tools import TOOLS, tool_to_command


@pytest.mark.parametrize(
    ("name", "arguments", "expected"),
    [
        ("open_app", {"name": "Spotify"}, "open Spotify"),
        ("open_link", {"url": "https://github.com"}, "open https://github.com"),
        ("open_project", {"name": "Venus"}, "open project Venus"),
        ("search_site", {"site": "youtube", "words": "lofi"}, "youtube lofi"),
    ],
)
def test_tool_call_becomes_command_text(name, arguments, expected):
    assert tool_to_command(name, arguments) == expected


def test_unknown_tool_is_rejected():
    with pytest.raises(ValueError):
        tool_to_command("delete_files", {"path": "C:/"})


def test_save_memory_is_offered_to_luna():
    assert "save_memory" in [tool["name"] for tool in TOOLS]
