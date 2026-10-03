import re

CANCEL = "cancel"
SLEEP = "sleep"

# Whole sentence only, so "stop the music" still goes to Luna.
CANCEL_PHRASES = {"stop", "cancel", "never mind", "nevermind", "forget it", "nothing"}
SLEEP_PHRASES = {"stop listening", "go to sleep", "sleep", "sleep mode", "go to sleep mode", "go to sleep now", "sleep now"}
POLITE_START = ["can you", "could you", "can u", "please"]
POLITE_END = ["please", "now"]


def control_word(text: str, wake_phrases: list[str]) -> str | None:
    """CANCEL or SLEEP when the whole sentence is a stop phrase, else None."""
    words = re.sub(r"[^a-z' ]", " ", text.lower()).split()
    # "Hey Venus, stop listening": the wake phrase is often in the recording too.
    for phrase in sorted(wake_phrases, key=len, reverse=True):
        target = phrase.split()
        if words[: len(target)] == target:
            words = words[len(target):]
            break
    rest = " ".join(words)
    for start in POLITE_START:
        rest = rest.removeprefix(start + " ")
    for end in POLITE_END:
        rest = rest.removesuffix(" " + end)
    if rest in SLEEP_PHRASES:
        return SLEEP
    if rest in CANCEL_PHRASES:
        return CANCEL
    return None


def resume_phrases(wake_phrases: list[str]) -> list[str]:
    """What wakes Venus from sleep: "<wake phrase> start listening"."""
    return [f"{phrase} start listening" for phrase in wake_phrases]
