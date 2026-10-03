from venus_node.voice.speakable import speakable


def test_speakable_keeps_short_text():
    assert speakable("  Opening Spotify for you.  ") == "Opening Spotify for you."


def test_speakable_cuts_long_text_at_last_sentence_end():
    text = "First one. Second one! Third one is far too long to fit"

    assert speakable(text, limit=30) == "First one. Second one!"


def test_speakable_without_sentence_end_cuts_at_a_space():
    assert speakable("one two three four", limit=10) == "one two"
