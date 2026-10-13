"""Home phrases: "turn off the bedroom light", "tv volume 20", "wake laptop".

Rules first, like opening apps: they're instant, free and predictable. Luna's
control_home tool writes the same kind of sentence, so both go through here.
"""

import re
from dataclasses import dataclass
from uuid import UUID

from features.commands.text_parser import CommandTextError
from features.home.models.home_device import HomeDevice

COLORS = {
    "red": "#ff0000",
    "green": "#00ff00",
    "blue": "#0000ff",
    "white": "#ffffff",
    "warm white": "#ffd8a8",
    "yellow": "#ffff00",
    "orange": "#ff8000",
    "purple": "#8000ff",
    "pink": "#ff40a0",
    "cyan": "#00ffff",
}
DIM = 30
FILLER_START = ("hey venus ", "venus ", "please ", "can you ", "could you ")
FILLER_END = (" please", " for me", " venus")
THIS_PC = {"pc", "computer", "my pc", "this pc", "my computer", "this computer", "sound", "speakers"}
TV_WORDS = {"tv", "television", "the tv"}
LIGHT_WORDS = {"light", "lamp"}
ALL_LIGHTS = {"lights", "all lights", "all the lights", "the lights", "every light"}
# Words that mean the owner meant a home device, so an unknown name is an answer, not "maybe an app".
HOME_WORDS = ("light", "lamp", "plug", "tv", "television", "fan")


class HomeTextError(CommandTextError):
    """A home phrase Venus understood but can't do; the message is her answer."""


@dataclass(frozen=True)
class HomeIntent:
    device: str  # light, plug, tv, wake or pc (this PC)
    action: str
    label: str
    home_device_id: UUID | None = None
    value: int | None = None
    color: str | None = None


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text.lower().strip().rstrip(".!?,;:")).strip()
    changed = True
    while changed:
        changed = False
        for start in FILLER_START:
            if text.startswith(start):
                text, changed = text[len(start):], True
        for end in FILLER_END:
            if text.endswith(end):
                text, changed = text[: -len(end)], True
    return text.strip()


def strip_article(name: str) -> str:
    return re.sub(r"^(the|my) ", "", name.strip())


def title(name: str) -> str:
    return name[:1].upper() + name[1:]


def percent(raw: str) -> int:
    value = int(raw)
    if value > 100:
        raise HomeTextError("Pick a number from 0 to 100")
    return value


def by_name(name: str, devices: list[HomeDevice], kinds: set[str]) -> list[HomeDevice] | None:
    """The devices a name means, or None if it isn't one of yours."""
    name = strip_article(name)
    exact = [d for d in devices if d.kind in kinds and d.name == name]
    if exact:
        return exact
    lights = [d for d in devices if d.kind == "light" and "light" in kinds]
    if name in ALL_LIGHTS and lights:
        return lights
    if name in LIGHT_WORDS and lights:
        if len(lights) > 1:
            raise HomeTextError(f"Which light: {', '.join(d.name for d in lights)}?")
        return lights
    tvs = [d for d in devices if d.kind == "tv" and "tv" in kinds]
    if name in TV_WORDS and tvs:
        return tvs[:1]
    return None


def unknown(name: str) -> HomeTextError | None:
    name = strip_article(name)
    if name in TV_WORDS:
        return HomeTextError("There's no TV in Settings, Home yet. Add it there first.")
    if any(word in name for word in HOME_WORDS):
        return HomeTextError(f"I don't have a device called {name}. Add it in Settings, Home.")
    return None


def tv_or_pc(target: str | None, devices: list[HomeDevice]) -> tuple[str, HomeDevice | None]:
    """Volume and mute go to the TV when it's named, else this PC."""
    target = strip_article(target or "")
    if not target or target in THIS_PC:
        return "pc", None
    found = by_name(target, devices, {"tv"})
    if found:
        return "tv", found[0]
    error = unknown(target)
    if error:
        raise error
    raise HomeTextError(f"I can change the volume of this PC or a TV, not {target}.")


def volume_intent(target: str | None, action: str, devices: list[HomeDevice], value: int | None = None) -> HomeIntent:
    kind, device = tv_or_pc(target, devices)
    who = "TV" if kind == "tv" else "This PC"
    words = {"volume_up": "volume up", "volume_down": "volume down", "mute": "mute", "unmute": "unmute"}
    what = f"volume {value}" if action == "volume_set" else words[action]
    return HomeIntent(kind, action, f"{who}: {what}", device.id if device else None, value)


def light_intents(name: str, devices: list[HomeDevice], action: str, value=None, color=None, label=""):
    found = by_name(name, devices, {"light", "plug"})
    if found is None:
        error = unknown(name)
        if error:
            raise error
        return None
    if action in ("brightness", "color") and any(d.kind == "plug" for d in found):
        raise HomeTextError("A plug can only turn on or off")
    return [
        HomeIntent(d.kind, action, f"{title(d.name)}: {label}", d.id, value, color)
        for d in found
    ]


VOLUME_SET = re.compile(r"^(?:turn |set )?(?:the |my )?(?:(?P<target>.+?) )?volume (?:to |at )?(?P<value>\d{1,3})(?: ?%| percent)?$")
VOLUME_STEP = re.compile(r"^(?:turn )?(?:the |my )?(?:(?P<target>.+?) )?volume (?P<dir>up|down)$")
TURN_UP = re.compile(r"^turn (?:the |my )?(?P<target>.+?) (?P<dir>up|down)$")
MUTE = re.compile(r"^(?P<action>mute|unmute) (?:the |my )?(?P<target>.+)$")
LOCK = re.compile(r"^lock (?:the |my |this )?(?:pc|computer|screen)$")
WAKE = re.compile(r"^(?:wake(?: up)?|boot(?: up)?) (?P<name>.+)$")
ON_OFF = re.compile(r"^(?:turn|switch|put) (?P<state>on|off) (?P<name>.+)$")
ON_OFF_AFTER = re.compile(r"^(?:turn|switch) (?P<name>.+?) (?P<state>on|off)$")
BRIGHTNESS = re.compile(r"^(?:set |turn |make )?(?P<name>.+?) (?:brightness )?(?:to |at )?(?P<value>\d{1,3}) ?(?:%|percent)$")
DIM_OR_BRIGHTEN = re.compile(r"^(?P<how>dim|brighten) (?P<name>.+)$")
COLOR = re.compile(
    r"^(?:set|make|turn|change) (?P<name>.+?) (?:to |colou?r to |colou?r )?(?P<color>#[0-9a-f]{6}|"
    + "|".join(sorted(COLORS, key=len, reverse=True))
    + r")$"
)


def parse_home_text(text: str, devices: list[HomeDevice]) -> list[HomeIntent] | None:
    """What to do at home, None if this isn't a home phrase, or HomeTextError as an answer."""
    text = clean(text)

    if LOCK.match(text):
        return [HomeIntent("pc", "lock", "This PC: lock")]

    if match := MUTE.match(text):
        target = match["target"]
        # "mute the mic" is the voice loop's own command, not the speakers.
        if strip_article(target) in ("mic", "microphone", "yourself"):
            return None
        return [volume_intent(target, match["action"], devices)]

    if match := VOLUME_SET.match(text):
        return [volume_intent(match["target"], "volume_set", devices, percent(match["value"]))]

    if match := VOLUME_STEP.match(text) or TURN_UP.match(text):
        target = match["target"]
        if TURN_UP.match(text) and not VOLUME_STEP.match(text):
            # "turn the tv up": only for things with a volume.
            if strip_article(target) not in THIS_PC and not by_name(target, devices, {"tv"}):
                return None
        return [volume_intent(target, f"volume_{match['dir']}", devices)]

    if match := WAKE.match(text):
        return wake_intents(match["name"], devices)

    if match := ON_OFF.match(text) or ON_OFF_AFTER.match(text):
        name, state = match["name"], match["state"]
        pcs = by_name(name, devices, {"pc"})
        if pcs:
            if state == "off":
                raise HomeTextError("I can wake another PC, but not turn one off yet.")
            return wake_intents(name, devices)
        if by_name(name, devices, {"tv"}):
            raise HomeTextError("I can only change the TV's volume for now, not turn it on or off.")
        return light_intents(name, devices, state, label=state)

    if match := DIM_OR_BRIGHTEN.match(text):
        value = DIM if match["how"] == "dim" else 100
        return light_intents(match["name"], devices, "brightness", value=value, label=f"{value}%")

    if match := BRIGHTNESS.match(text):
        value = percent(match["value"])
        return light_intents(match["name"], devices, "brightness", value=value, label=f"{value}%")

    if match := COLOR.match(text):
        color = COLORS.get(match["color"], match["color"])
        return light_intents(match["name"], devices, "color", color=color, label=match["color"])

    return None


def wake_intents(name: str, devices: list[HomeDevice]) -> list[HomeIntent] | None:
    found = by_name(name, devices, {"pc"})
    if found is None:
        name = strip_article(name)
        if name in THIS_PC:
            raise HomeTextError("I run on this PC, so it's already awake.")
        return None
    return [HomeIntent("wake", "wake", f"Wake {d.name}", d.id) for d in found]
