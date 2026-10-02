import pytest

from features.chat.prompt import BASE_PROMPT, build_instructions, plain_punctuation


def test_build_instructions_stacks_base_personality_then_project():
    text = build_instructions("Be flirty.", "Help with my Java assignment.")

    assert text == f"{BASE_PROMPT}\n\nBe flirty.\n\nHelp with my Java assignment."


def test_build_instructions_skips_empty_parts():
    assert build_instructions(None, "   ") == BASE_PROMPT


def test_build_instructions_lists_sites_and_folders_after_base_rules():
    text = build_instructions("Be flirty.", None, ["youtube", "comix"], ["Venus"])
    parts = text.split("\n\n")

    assert parts[0] == BASE_PROMPT
    assert parts[1].startswith("Saved sites: comix, youtube.")
    assert "search_site" in parts[1]
    assert parts[2].startswith("Project folders on the PC: Venus.")
    assert parts[3] == "Be flirty."


def test_build_instructions_lists_owner_facts_before_personality():
    text = build_instructions("Be flirty.", None, memories=["Owner name is Umar."])
    parts = text.split("\n\n")

    assert parts[1] == "What you know about the owner: Owner name is Umar."
    assert parts[2] == "Be flirty."


def test_build_instructions_without_facts_has_no_owner_line():
    assert "What you know" not in build_instructions(None, None, memories=[])


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("I love you too, Umar; you've got me.", "I love you too, Umar, you've got me."),
        ("Opening it now\u2014enjoy, love.", "Opening it now, enjoy, love."),
        ("Sure \u2013 here you go", "Sure, here you go"),
        ("Fine - whatever you want", "Fine, whatever you want"),
        ("Done,; love", "Done, love"),
    ],
)
def test_plain_punctuation_swaps_bot_pauses_for_commas(text, expected):
    assert plain_punctuation(text) == expected


def test_plain_punctuation_keeps_hyphenated_words():
    assert plain_punctuation("I like lo-fi and sci-fi.") == "I like lo-fi and sci-fi."
