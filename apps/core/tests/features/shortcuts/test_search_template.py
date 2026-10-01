import pytest

from features.shortcuts.search_template import SearchTemplateError, search_template


def test_link_with_words_slot_is_kept():
    link = "https://comix.to/browse?q={words}"

    assert search_template(link) == link


def test_search_parameter_becomes_words_slot_and_others_stay():
    link = "https://comix.to/browse?q=solo%20leveling&sort=relevance%3Adesc"

    assert search_template(link) == (
        "https://comix.to/browse?q={words}&sort=relevance%3Adesc"
    )


def test_search_parameter_with_plus_spaces():
    link = "https://asurascans.com/browse?search=solo+leveling"

    assert search_template(link) == "https://asurascans.com/browse?search={words}"


def test_empty_search_parameter_becomes_words_slot():
    assert search_template("https://x.com/?q=") == "https://x.com/?q={words}"


def test_search_words_found_in_path():
    link = "https://x.com/search/Solo-Leveling"

    assert search_template(link, "solo leveling") == "https://x.com/search/{words}"


def test_link_without_search_raises():
    with pytest.raises(SearchTemplateError):
        search_template("https://x.com/browse", "naruto")
