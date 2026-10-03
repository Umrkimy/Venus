import re

WORD = re.compile(r"[A-Za-z]+")

# Spellings that sound the same, from longest to shortest.
SAME_SOUND = [("ph", "f"), ("cks", "x"), ("ks", "x"), ("cs", "x"), ("ck", "k"),
              ("c", "k"), ("q", "k"), ("z", "s")]

# Very short keywords would swap too many ordinary words.
MIN_KEYWORD = 4


def sound_key(word: str) -> str:
    """Rough sound of a word: "comics" and "comix" both give "komix"."""
    key = word.lower()
    for spelling, sound in SAME_SOUND:
        key = key.replace(spelling, sound)
    # "comixx" and "comix" sound the same.
    return re.sub(r"(.)\1+", r"\1", key)


def fix_keywords(text: str, keywords: list[str]) -> str:
    """Swap heard words for the shortcut keyword they sound like."""
    sounds = {
        sound_key(keyword): keyword
        for keyword in keywords
        if keyword.isalpha() and len(keyword) >= MIN_KEYWORD
    }

    def swap(match: re.Match[str]) -> str:
        word = match.group()
        keyword = sounds.get(sound_key(word))
        if keyword is None or word.lower() == keyword.lower():
            return word
        return keyword

    return WORD.sub(swap, text)
