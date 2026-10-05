import re

CANCEL = "cancel"
SLEEP = "sleep"
MUTE = "mute"
GOODBYE = "goodbye"

# Whole sentence only, so "stop the music" still goes to Luna.
CANCEL_PHRASES = {"stop", "cancel", "never mind", "nevermind", "forget it", "nothing"}
SLEEP_PHRASES = {"stop listening", "go to sleep", "sleep", "sleep mode", "go to sleep mode", "go to sleep now", "sleep now"}
MUTE_PHRASES = {
    "mute", "mute mic", "mute the mic", "mute my mic", "mute microphone", "mute the microphone",
    "mute yourself", "turn off the mic", "turn off mic", "turn the mic off", "mic off",
}
# Said over Luna while she talks or thinks. With her name, so her own voice
# through the speakers ("...stop by later...") doesn't cut her off.
STOP_TALKING_PHRASES = ["stop venus", "venus stop", "never mind venus", "hey venus stop"]
# Ends a conversation after Luna says bye back.
GOODBYE_PHRASES = {
    "goodbye", "bye", "bye bye", "okay goodbye", "ok goodbye", "okay bye", "ok bye",
    "goodbye venus", "bye venus", "thats all", "that's all", "see you", "see you later",
    "good night", "goodnight", "talk later", "talk to you later",
    # Thanks with her name closes it; plain "thank you" keeps the conversation going.
    "thank you venus", "thanks venus",
}
# Around a stop or a bye these change nothing: "thank you, stop", "okay goodbye now".
END_FILLER = {"thank", "thanks", "you", "okay", "ok", "alright", "now", "venus", "please", "so", "and"}
STOP_WORDS = {"stop", "cancel"}
BYE_WORDS = {"bye", "goodbye"}
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
    """CANCEL, SLEEP, MUTE or GOODBYE when the whole sentence is one, else None."""
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
    if rest in GOODBYE_PHRASES:
        return GOODBYE
    return mixed_ending(rest.split())


def mixed_ending(words: list[str]) -> str | None:
    """GOODBYE or CANCEL for endings like "thank you, stop" or "okay bye bye venus".

    Only when nothing but filler is left around the stop or bye words, so
    "stop the music" or "say bye to my mom" still go to Luna.
    """
    rest = [word for word in words if word not in END_FILLER]
    if not rest or not all(word in STOP_WORDS | BYE_WORDS for word in rest):
        return None
    # A bye anywhere: Luna says bye back. Only stop: end quietly.
    return GOODBYE if any(word in BYE_WORDS for word in rest) else CANCEL


def resume_phrases(wake_phrases: list[str]) -> list[str]:
    """What wakes Venus from sleep: "<wake phrase> start listening"."""
    return [f"{phrase} start listening" for phrase in wake_phrases]
