import re
from datetime import datetime
from zoneinfo import ZoneInfo

# Fixed rules: editing a personality can't remove these.
BASE_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something. "
    # History shows earlier asks; without this, "thanks" after "open comix" opened it again.
    "Earlier requests in the chat are already done: only use a tool for something the "
    "owner asks in their newest message, never to redo an earlier one. "
    "When you use a tool, also write one short sentence telling the owner what you're doing. "
    "Talk like a real person texting, not an assistant: natural, casual words. "
    "Use only commas, periods, question marks and exclamation marks. "
    "Never semicolons or dashes. No emoji. "
    "Never use assistant phrases like \"How can I assist you?\" or \"As an AI\"."
)

# Not in Full mode: her line is written before anything opens.
APPROVE_FIRST = (
    "Nothing opens until the owner presses Approve, so say you're ready to open it, "
    "not that it's open."
)

# A semicolon, a long dash, or a hyphen with spaces around it, used as a pause.
BOT_PAUSE = re.compile(r"\s*(?:[;\u2014\u2013]|\s-\s)\s*")


def build_instructions(
    personality: str | None,
    project: str | None,
    sites: list[str] | None = None,
    folders: list[str] | None = None,
    memories: list[str] | None = None,
    approve_first: bool = False,
    now: str | None = None,
) -> str:
    """Base rules, what's on the PC and the owner, who Venus is, the project, then the time."""
    parts = [
        BASE_PROMPT,
        APPROVE_FIRST if approve_first else None,
        sites_line(sites or []),
        folders_line(folders or []),
        memories_line(memories or []),
        personality,
        project,
        # Last: it changes every minute, and everything before it stays the
        # same, so OpenAI can reuse (cache) that start of the prompt.
        now,
    ]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def now_line(now_utc: datetime, time_zone: str | None, country: str = "") -> str:
    """The owner's date and time, so Luna never guesses them."""
    if not time_zone:
        return (
            f"Right now it is {spoken_time(now_utc)} UTC. The owner has not set "
            "a time zone yet: if they ask the time, give it in UTC and say they "
            "can set theirs in Settings, General."
        )
    local = now_utc.astimezone(ZoneInfo(time_zone))
    line = f"Right now for the owner it is {spoken_time(local)} ({time_zone})."
    if country:
        line += f" The owner lives in {country}."
    return line + " Use this for anything about the time, the date or the day."


def spoken_time(moment: datetime) -> str:
    # "Tuesday 6 October 2026, 2:30 PM": no leading zeros, no 24-hour clock.
    hour = moment.hour % 12 or 12
    half = "AM" if moment.hour < 12 else "PM"
    return f"{moment:%A} {moment.day} {moment:%B %Y}, {hour}:{moment:%M} {half}"


def sites_line(sites: list[str]) -> str | None:
    # Without this Luna guesses addresses; "open <keyword>" uses the saved one.
    if not sites:
        return None
    return (
        f"Saved sites: {', '.join(sorted(sites))}. "
        "If the owner names something to find there (search, look up, find, "
        "a title), call search_site with its keyword and those words, even when "
        "they also say open. Opening and searching the same site is one "
        "search_site call, never also open_app. Only when there is nothing to "
        "find, call open_app with its keyword."
    )


def folders_line(folders: list[str]) -> str | None:
    # "open code venus" means the Venus folder in VS Code, not an app.
    if not folders:
        return None
    return (
        f"Project folders on the PC: {', '.join(folders)}. "
        "When the owner wants one of them or says code plus its name, "
        "call open_project with the folder name."
    )


def memories_line(memories: list[str]) -> str | None:
    # Facts the owner asked Venus to keep, shared by every chat.
    if not memories:
        return None
    facts = " ".join(fact.rstrip(".") + "." for fact in memories)
    return f"What you know about the owner: {facts}"


# A tool call written out as words, e.g. {"keyword":"spotify"} to=open_app.
TOOL_ECHO = re.compile(r"\{[^{}]*\}\s*to=[\w.]+")


def plain_punctuation(text: str) -> str:
    """Swap pauses that read like a bot for commas, in case Luna slips.

    Also drops tool calls she sometimes types out instead of calling.
    """
    text = TOOL_ECHO.sub("", text).strip()
    text = BOT_PAUSE.sub(", ", text)
    return re.sub(r",(\s*,)+", ",", text).strip(" ,")
