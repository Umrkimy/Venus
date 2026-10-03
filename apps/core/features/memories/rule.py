import re

# "remember I like lo-fi", "save this: my birthday is 3 May".
MEMORY_PATTERN = re.compile(
    r"^\s*(?:remember(?:\s+that)?|save\s+this)\s*[:,-]?\s*(?P<fact>.+?)\s*$",
    re.IGNORECASE | re.DOTALL,
)

# "remember when we...", "remember how I fixed it?": a question, not a fact.
QUESTION = re.compile(r"(?:^(?:when|how|what|where|who|why|if)\b|\?$)", re.IGNORECASE)

# "... and open spotify": more to do, so Luna handles the whole message.
MORE_WORK = re.compile(
    r"\b(?:and|then)\s+(?:also\s+)?(?:open|search|play|launch|start|close|find)\b",
    re.IGNORECASE,
)


def memory_from_message(message: str) -> str | None:
    """The fact to save when the owner asks Venus to remember something."""
    match = MEMORY_PATTERN.match(message)
    if match is None:
        return None
    fact = match.group("fact")
    if QUESTION.search(fact) or MORE_WORK.search(fact):
        return None
    return fact[:300]
