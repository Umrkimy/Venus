# Fixed rules: editing a personality can't remove these.
BASE_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something."
)


def build_instructions(
    personality: str | None,
    project: str | None,
    sites: list[str] | None = None,
    folders: list[str] | None = None,
) -> str:
    """Base rules and what's on the PC, then who Venus is, then the project."""
    parts = [
        BASE_PROMPT,
        sites_line(sites or []),
        folders_line(folders or []),
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
        "they also say open. Only when there is nothing to find, call open_app "
        "with its keyword."
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
