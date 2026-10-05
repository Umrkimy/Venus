import re

CANCEL = "cancel"
SLEEP = "sleep"
MUTE = "mute"

# Whole sentence only, so "stop the music" still goes to Luna.
CANCEL_PHRASES = {"stop", "cancel", "never mind", "nevermind", "forget it", "nothing"}
SLEEP_PHRASES = {"stop listening", "go to sleep", "sleep", "sleep mode", "go to sleep mode", "go to sleep now", "sleep now"}
MUTE_PHRASES = {
    "mute", "mute mic", "mute the mic", "mute my mic", "mute microphone", "mute the microphone",
    "mute yourself", "turn off the mic", "turn off mic", "turn the mic off", "mic off",
}
POLITE_START = ["can you", "could you", "can u", "please"]
POLITE_END = ["please", "now", "for me"]


def said_once(words: list[str]) -> list[str]:
    """"sleep mode sleep mode" -> "sleep mode": people repeat a command when unsure it was heard."""
    for times in (3, 2):
        size = len(words) // times
        if size and words == words[:size] * times:
            return words[:size]
    return words


def control_word(text: str, wake_phrases: list[str]) -> str | None:
    """CANCEL, SLEEP or MUTE when the whole sentence is a stop phrase, else None."""
    words = re.sub(r"[^a-z' ]", " ", text.lower()).split()
    # "Hey Venus, stop listening": the wake phrase is often in the recording too.
    for phrase in sorted(wake_phrases, key=len, reverse=True):
        target = phrase.split()
        if words[: len(target)] == target:
            words = words[len(target):]
            break
    rest = " ".join(said_once(words))
    for start in POLITE_START:
        rest = rest.removeprefix(start + " ")
    for end in POLITE_END:
        rest = rest.removesuffix(" " + end)
    if rest in SLEEP_PHRASES:
        return SLEEP
    if rest in MUTE_PHRASES:
        return MUTE
    if rest in CANCEL_PHRASES:
        return CANCEL
    return None


def resume_phrases(wake_phrases: list[str]) -> list[str]:
    """What wakes Venus from sleep: "<wake phrase> start listening"."""
    return [f"{phrase} start listening" for phrase in wake_phrases]
