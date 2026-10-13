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


@pytest.mark.parametrize(
    ("arguments", "expected"),
    [
        ({"device": "bedroom light", "action": "off"}, "turn off bedroom light"),
        ({"device": "bedroom light", "action": "brightness", "value": 30}, "set bedroom light to 30%"),
        ({"device": "bedroom light", "action": "color", "color": "red"}, "set bedroom light to red"),
        ({"device": "tv", "action": "volume_up"}, "tv volume up"),
        ({"device": "tv", "action": "volume_set", "value": 20}, "set tv volume to 20"),
        ({"device": "tv", "action": "mute"}, "mute tv"),
        ({"device": "laptop", "action": "wake"}, "wake laptop"),
        ({"device": "pc", "action": "lock"}, "lock pc"),
    ],
)
def test_control_home_becomes_a_sentence_the_home_rules_understand(arguments, expected):
    from datetime import datetime, timezone

    from features.home.models.home_device import HomeDevice
    from features.home.rules import parse_home_text

    sentence = tool_to_command("control_home", arguments)

    assert sentence == expected
    now = datetime.now(timezone.utc)
    devices = [
        HomeDevice("bedroom light", "light", now, address="192.168.1.40", tuya_id="a", local_key_encrypted="x"),
        HomeDevice("tv", "tv", now, address="192.168.1.50"),
        HomeDevice("laptop", "pc", now, mac="AA:BB:CC:DD:EE:FF"),
    ]
    intents = parse_home_text(sentence, devices)
    assert intents is not None and intents[0].action == arguments["action"]
