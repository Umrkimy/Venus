import re

# Fixed rules: editing a personality can't remove these.
BASE_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something. "
    "Talk like a real person texting, not an assistant: natural, casual words. "
    "Use only commas, periods, question marks and exclamation marks. "
    "Never semicolons or dashes. No emoji. "
    "Never use assistant phrases like \"How can I assist you?\" or \"As an AI\"."
)

# A semicolon, a long dash, or a hyphen with spaces around it, used as a pause.
BOT_PAUSE = re.compile(r"\s*(?:[;\u2014\u2013]|\s-\s)\s*")


def build_instructions(
    personality: str | None,
    project: str | None,
    sites: list[str] | None = None,
    folders: list[str] | None = None,
    memories: list[str] | None = None,
) -> str:
    """Base rules, what's on the PC and the owner, then who Venus is, then the project."""
    parts = [
        BASE_PROMPT,
        sites_line(sites or []),
        folders_line(folders or []),
        memories_line(memories or []),
        personality,
        project,
    ]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


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
