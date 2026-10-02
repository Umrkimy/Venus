from features.chat.prompt import BASE_PROMPT, build_instructions


def test_build_instructions_stacks_base_personality_then_project():
    text = build_instructions("Be flirty.", "Help with my Java assignment.")

    assert text == f"{BASE_PROMPT}\n\nBe flirty.\n\nHelp with my Java assignment."


def test_build_instructions_skips_empty_parts():
    assert build_instructions(None, "   ") == BASE_PROMPT


def test_build_instructions_lists_saved_sites_after_base_rules():
    text = build_instructions("Be flirty.", None, ["youtube", "comix"])

    assert text == (
        f"{BASE_PROMPT}\n\n"
        "Saved sites: comix, youtube. To open one, call open_app with its keyword.\n\n"
        "Be flirty."
    )
