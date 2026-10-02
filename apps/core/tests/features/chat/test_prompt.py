from features.chat.prompt import BASE_PROMPT, build_instructions


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
