import pytest

from features.voice.sound_alike import fix_keywords, sound_key


def test_same_sounding_words_share_a_key():
    assert sound_key("comics") == sound_key("comix")
    assert sound_key("Comics") == sound_key("comix")


@pytest.mark.parametrize(
    ("heard", "fixed"),
    [
        ("Search comics for Solo Leveling.", "Search comix for Solo Leveling."),
        ("Open Comics.", "Open comix."),
        # A keyword already heard right stays as it was said.
        ("open Comix", "open Comix"),
        # Words that only look a bit alike stay.
        ("open comic", "open comic"),
        ("open spotify", "open spotify"),
    ],
)
def test_fix_keywords_swaps_sound_alikes(heard, fixed):
    assert fix_keywords(heard, ["comix", "asura"]) == fixed


def test_short_keywords_are_left_alone():
    # "yt" would sound like too many everyday words.
    assert fix_keywords("open it", ["yt"]) == "open it"
