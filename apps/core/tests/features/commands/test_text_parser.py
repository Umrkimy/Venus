import pytest

from venus_protocol.schemas.connections import NodeApp

from features.commands.text_parser import (
    CommandTextError,
    SearchSite,
    parse_command_text,
)

APPS = [
    NodeApp(name="Spotify", app_id="spotify"),
    NodeApp(name="Steam", app_id="steam"),
    NodeApp(name="Notepad", app_id="notepad"),
    NodeApp(name="Notepad++", app_id="notepad-plus"),
    NodeApp(name="Notion", app_id="notion"),
]
PROJECTS = ["Venus", "fastapi_blog"]


def parse(text: str, **kwargs):
    return parse_command_text(text, APPS, PROJECTS, **kwargs)


def test_exact_app_name_opens_that_app():
    parsed = parse("open notepad")

    assert parsed.application_id == "notepad"
    assert parsed.label == "Notepad"


def test_start_of_app_name_opens_the_only_match():
    parsed = parse("open spot")

    assert parsed.application_id == "spotify"
    assert parsed.label == "Spotify"


def test_several_matching_apps_ask_which_one():
    with pytest.raises(CommandTextError) as error:
        parse("open no")

    assert str(error.value) == "Which one: Notepad, Notepad++, Notion?"


def test_unknown_app_is_rejected():
    with pytest.raises(CommandTextError) as error:
        parse("open photoshop")

    assert str(error.value) == "No app called photoshop on this PC"


@pytest.mark.parametrize("text", ["open project venus", "Open my project VENUS"])
def test_project_opens_with_its_real_spelling(text: str):
    parsed = parse(text)

    assert parsed.project_name == "Venus"
    assert parsed.label == "Venus in VS Code"


def test_unknown_project_is_rejected():
    with pytest.raises(CommandTextError) as error:
        parse("open project secret")

    assert str(error.value) == "No project called secret on this PC"


def test_site_with_words_searches_and_encodes_them():
    parsed = parse("youtube teo & co")

    assert parsed.url == "https://www.youtube.com/results?search_query=teo+%26+co"
    assert parsed.label == "YouTube search: teo & co"


def test_site_without_words_opens_its_home_page():
    parsed = parse("Netflix")

    assert parsed.url == "https://www.netflix.com"
    assert parsed.label == "Netflix"


def test_site_without_search_address_cannot_search():
    sites = {"comix": SearchSite(label="Comix", home_url="https://comix.to")}

    assert parse("comix", sites=sites).url == "https://comix.to"
    with pytest.raises(CommandTextError) as error:
        parse("comix solo leveling", sites=sites)

    assert str(error.value) == "Comix can't search yet, only open"


@pytest.mark.parametrize(
    ("text", "url"),
    [
        ("github.com", "https://github.com"),
        ("open github.com", "https://github.com"),
        ("http://example.com", "http://example.com"),
    ],
)
def test_link_opens_with_https_added_when_missing(text: str, url: str):
    assert parse(text).url == url


@pytest.mark.parametrize("text", ["hello there", "open", "   "])
def test_text_venus_does_not_understand_is_rejected(text: str):
    with pytest.raises(CommandTextError) as error:
        parse(text)

    assert str(error.value) == "Venus didn't understand that"
