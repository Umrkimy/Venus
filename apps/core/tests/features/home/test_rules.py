from datetime import datetime, timezone

import pytest

from features.home.models.home_device import HomeDevice
from features.home.rules import HomeTextError, parse_home_text

NOW = datetime.now(timezone.utc)
BEDROOM = HomeDevice("bedroom light", "light", NOW, address="192.168.1.40", tuya_id="a", local_key_encrypted="x")
DESK = HomeDevice("desk lamp", "light", NOW, address="192.168.1.41", tuya_id="b", local_key_encrypted="x")
FAN = HomeDevice("fan", "plug", NOW, address="192.168.1.42", tuya_id="c", local_key_encrypted="x")
TV = HomeDevice("living room tv", "tv", NOW, address="192.168.1.50")
LAPTOP = HomeDevice("laptop", "pc", NOW, mac="AA:BB:CC:DD:EE:FF")
DEVICES = [BEDROOM, DESK, FAN, TV, LAPTOP]


def one(text: str, devices=DEVICES):
    intents = parse_home_text(text, devices)
    assert intents is not None and len(intents) == 1, intents
    intent = intents[0]
    return intent.device, intent.action, intent.value, intent.color, intent.home_device_id


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("turn off the bedroom light", ("light", "off", None, None, BEDROOM.id)),
        ("Turn the bedroom light on.", ("light", "on", None, None, BEDROOM.id)),
        ("hey venus switch on the fan please", ("plug", "on", None, None, FAN.id)),
        ("set bedroom light to 30%", ("light", "brightness", 30, None, BEDROOM.id)),
        ("desk lamp 70 percent", ("light", "brightness", 70, None, DESK.id)),
        ("dim the desk lamp", ("light", "brightness", 30, None, DESK.id)),
        ("make the bedroom light blue", ("light", "color", None, "#0000ff", BEDROOM.id)),
        ("set desk lamp to warm white", ("light", "color", None, "#ffd8a8", DESK.id)),
        ("set bedroom light to #12ab34", ("light", "color", None, "#12ab34", BEDROOM.id)),
        ("tv volume up", ("tv", "volume_up", None, None, TV.id)),
        ("turn the tv down", ("tv", "volume_down", None, None, TV.id)),
        ("set the living room tv volume to 20", ("tv", "volume_set", 20, None, TV.id)),
        ("mute the tv", ("tv", "mute", None, None, TV.id)),
        ("volume up", ("pc", "volume_up", None, None, None)),
        ("volume 40%", ("pc", "volume_set", 40, None, None)),
        ("unmute my pc", ("pc", "unmute", None, None, None)),
        ("lock my computer", ("pc", "lock", None, None, None)),
        ("wake up the laptop", ("wake", "wake", None, None, LAPTOP.id)),
        ("turn on my laptop", ("wake", "wake", None, None, LAPTOP.id)),
    ],
)
def test_home_phrases(text, expected):
    assert one(text) == expected


def test_all_the_lights_means_every_light_not_plugs():
    intents = parse_home_text("turn off all the lights", DEVICES)

    assert [i.home_device_id for i in intents] == [BEDROOM.id, DESK.id]
    assert intents[0].label == "Bedroom light: off"


def test_the_light_with_one_light_is_that_light():
    assert one("turn on the light", [BEDROOM, TV])[4] == BEDROOM.id


@pytest.mark.parametrize(
    ("text", "answer"),
    [
        ("turn on the light", "Which light: bedroom light, desk lamp?"),
        ("turn off the kitchen light", "I don't have a device called kitchen light"),
        ("turn on the tv", "only change this TV's volume"),
        ("turn off the laptop", "not turn one off"),
        ("set the fan to 50%", "A plug can only turn on or off"),
        ("tv volume 150", "from 0 to 100"),
        ("wake up this pc", "already awake"),
    ],
)
def test_understood_but_not_possible_is_an_answer(text, answer):
    with pytest.raises(HomeTextError, match=answer):
        parse_home_text(text, DEVICES)


def test_no_tv_yet_says_where_to_add_it():
    with pytest.raises(HomeTextError, match="Settings, Home"):
        parse_home_text("mute the tv", [BEDROOM])


@pytest.mark.parametrize(
    "text",
    ["open spotify", "turn on spotify", "mute the mic", "wake me up at 7", "what's the volume of a sphere", "youtube lofi"],
)
def test_other_things_are_left_to_the_app_rules_and_luna(text):
    assert parse_home_text(text, DEVICES) is None


# Imported from Home Assistant.
HA_TV = HomeDevice("tv", "tv", NOW, ha_entity_id="media_player.living_room")
AC = HomeDevice("bedroom aircon", "aircon", NOW, ha_entity_id="climate.bedroom")
MOVIE = HomeDevice("movie time", "scene", NOW, ha_entity_id="scene.movie_time")
HA_DEVICES = [BEDROOM, HA_TV, AC, MOVIE]


def full(text: str, devices=HA_DEVICES):
    intents = parse_home_text(text, devices)
    assert intents is not None and len(intents) == 1, intents
    intent = intents[0]
    return intent.device, intent.action, intent.value, intent.mode, intent.home_device_id


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("turn on the tv", ("tv", "on", None, None, HA_TV.id)),
        ("switch the tv off", ("tv", "off", None, None, HA_TV.id)),
        ("tv volume 20", ("tv", "volume_set", 20, None, HA_TV.id)),
        ("turn on the aircon", ("aircon", "on", None, None, AC.id)),
        ("turn off the ac please", ("aircon", "off", None, None, AC.id)),
        ("set the aircon to 24", ("aircon", "temperature", 24, None, AC.id)),
        ("bedroom aircon 22 degrees", ("aircon", "temperature", 22, None, AC.id)),
        ("set the air con temperature to 25°c", ("aircon", "temperature", 25, None, AC.id)),
        ("set the aircon to cool", ("aircon", "mode", None, "cool", AC.id)),
        ("put the ac on fan mode", ("aircon", "mode", None, "fan_only", AC.id)),
        ("movie time", ("scene", "activate", None, None, MOVIE.id)),
        ("hey venus movie time please", ("scene", "activate", None, None, MOVIE.id)),
        ("start movie time", ("scene", "activate", None, None, MOVIE.id)),
        ("activate the movie time scene", ("scene", "activate", None, None, MOVIE.id)),
        ("turn on movie time", ("scene", "activate", None, None, MOVIE.id)),
    ],
)
def test_home_assistant_phrases(text, expected):
    assert full(text) == expected


def test_aircon_label_reads_well():
    assert parse_home_text("set the aircon to 24", HA_DEVICES)[0].label == "Bedroom aircon: 24°C"


@pytest.mark.parametrize(
    ("text", "devices", "answer"),
    [
        ("set the aircon to 40", HA_DEVICES, "Pick 16 to 30"),
        ("turn off movie time", HA_DEVICES, "only be started"),
        ("turn on the aircon", [BEDROOM], "no air-con in Settings, Home"),
        ("turn on the aircon", [AC, HomeDevice("office ac", "aircon", NOW, ha_entity_id="climate.office")],
         "Which air-con"),
    ],
)
def test_home_assistant_answers(text, devices, answer):
    with pytest.raises(HomeTextError, match=answer):
        parse_home_text(text, devices)


@pytest.mark.parametrize("text", ["play lofi", "start spotify", "set the bedroom light to 50", "set the timer to cool"])
def test_home_assistant_words_dont_steal_other_phrases(text):
    assert parse_home_text(text, HA_DEVICES) is None
