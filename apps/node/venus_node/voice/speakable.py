import re

SPEAK_LIMIT = 1000  # Core's /voice/speak refuses longer text

SENTENCE_END = re.compile(r"[.!?](?=\s|$)")


def speakable(text: str, limit: int = SPEAK_LIMIT) -> str:
    """The part of a reply Luna can say in one go, ending on a whole sentence."""
    text = text.strip()
    if len(text) <= limit:
        return text
    head = text[:limit]
    ends = [match.end() for match in SENTENCE_END.finditer(head)]
    # One giant sentence: cut at the last space instead of mid-word.
    cut = ends[-1] if ends else head.rfind(" ")
    return head[:cut if cut > 0 else limit].strip()
