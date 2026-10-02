from features.chat.prompt import BASE_PROMPT, build_instructions


def test_build_instructions_stacks_base_personality_then_project():
    text = build_instructions("Be flirty.", "Help with my Java assignment.")

    assert text == f"{BASE_PROMPT}\n\nBe flirty.\n\nHelp with my Java assignment."


def test_build_instructions_skips_empty_parts():
    assert build_instructions(None, "   ") == BASE_PROMPT
