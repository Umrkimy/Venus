import re

# "remember I like lo-fi", "save this: my birthday is 3 May".
MEMORY_PATTERN = re.compile(
    r"^\s*(?:remember(?:\s+that)?|save\s+this)\s*[:,-]?\s*(?P<fact>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)


def memory_from_message(message: str) -> str | None:
    """The fact to save when the owner asks Venus to remember something."""
    match = MEMORY_PATTERN.match(message)
    if match is None:
        return None
    return match.group("fact")[:300]
