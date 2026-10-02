# Fixed rules: editing a personality can't remove these.
BASE_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something."
)


def build_instructions(
    personality: str | None,
    project: str | None,
    sites: list[str] | None = None,
) -> str:
    """Base rules and saved sites, then who Venus is, then the project."""
    parts = [BASE_PROMPT, sites_line(sites or []), personality, project]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())


def sites_line(sites: list[str]) -> str | None:
    # Without this Luna guesses addresses; "open <keyword>" uses the saved one.
    if not sites:
        return None
    return (
        f"Saved sites: {', '.join(sorted(sites))}. "
        "To open one, call open_app with its keyword."
    )
