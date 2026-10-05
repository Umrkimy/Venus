from venus_node.voice.stop_words import CANCEL, MUTE, SLEEP, control_word, resume_phrases

WAKE = ["hey venus", "venus", "hey love"]


def test_stop_and_never_mind_cancel_the_turn():
    assert control_word("Stop.", WAKE) == CANCEL
    assert control_word("Never mind", WAKE) == CANCEL


def test_stop_listening_puts_venus_to_sleep_in_any_polite_form():
    assert control_word("Venus, stop listening.", WAKE) == SLEEP
    assert control_word("Hey Venus, can you stop listening?", WAKE) == SLEEP
    assert control_word("stop listening please", WAKE) == SLEEP


def test_longer_sentences_still_go_to_luna():
    assert control_word("Stop the music", WAKE) is None
    assert control_word("open spotify", WAKE) is None


def test_resume_phrase_is_wake_phrase_plus_start_listening():
    assert resume_phrases(["hey venus", "venus"]) == ["hey venus start listening", "venus start listening"]


def test_a_repeated_command_counts_once():
    assert control_word("Sleep mode, sleep mode.", WAKE) == SLEEP
    assert control_word("Stop. Stop. Stop.", WAKE) == CANCEL


def test_mute_the_mic_in_any_polite_form():
    assert control_word("Hey Venus, mute the mic for me.", WAKE) == MUTE
    assert control_word("Venus, can you mute yourself please", WAKE) == MUTE
    assert control_word("Mute the music", WAKE) is None
