# Fixed rules: editing a personality can't remove these.
BASE_PROMPT = (
    "Your name is Venus. Never say you are ChatGPT. "
    "Use a tool when the owner asks to open something."
)


def build_instructions(personality: str | None, project: str | None) -> str:
    """Base rules, then who Venus is, then what this project is about."""
    parts = [BASE_PROMPT, personality, project]
    return "\n\n".join(part.strip() for part in parts if part and part.strip())
