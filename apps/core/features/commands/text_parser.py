from dataclasses import dataclass
from urllib.parse import quote_plus

from venus_protocol.schemas.connections import NodeApp


class CommandTextError(ValueError):
    """The message is shown to the owner as is."""


class NotUnderstoodError(CommandTextError):
    """The rule parser has no rule for this text; the brain may answer."""


@dataclass(frozen=True)
class SearchSite:
    label: str
    home_url: str
    # None means the site can only be opened, not searched (D-53).
    search_url: str | None = None


@dataclass(frozen=True)
class ParsedCommand:
    label: str
    application_id: str | None = None
    project_name: str | None = None
    url: str | None = None


SEARCH_SITES = {
    "youtube": SearchSite(
        label="YouTube",
        home_url="https://www.youtube.com",
        search_url="https://www.youtube.com/results?search_query={words}",
    ),
    "netflix": SearchSite(
        label="Netflix",
        home_url="https://www.netflix.com",
        search_url="https://www.netflix.com/search?q={words}",
    ),
    "google": SearchSite(
        label="Google",
        home_url="https://www.google.com",
        search_url="https://www.google.com/search?q={words}",
    ),
}

PROJECT_PREFIXES = ("open my project ", "open project ")
MAX_CHOICES = 5


def parse_command_text(
    text: str,
    apps: list[NodeApp],
    projects: list[str],
    sites: dict[str, SearchSite] = SEARCH_SITES,
) -> ParsedCommand:
    text = text.strip()
    lowered = text.lower()

    if not text:
        raise NotUnderstoodError("Venus didn't understand that")

    for prefix in PROJECT_PREFIXES:
        if lowered.startswith(prefix):
            return _parse_project(text[len(prefix):].strip(), projects)

    first_word, _, rest = text.partition(" ")
    first_word = first_word.lower()
    rest = rest.strip()

    site = sites.get(first_word)
    if site is not None:
        return _parse_site(site, rest)

    if first_word == "open" and rest:
        if _looks_like_url(rest):
            return _parse_url(rest)
        # "open comix" means the shortcut, unless an app has exactly that name.
        site = sites.get(rest.lower())
        if site is not None and not any(app.name.lower() == rest.lower() for app in apps):
            return _parse_site(site, "")
        return _parse_app(rest, apps)

    if _looks_like_url(text):
        return _parse_url(text)

    raise NotUnderstoodError("Venus didn't understand that")


def _parse_project(name: str, projects: list[str]) -> ParsedCommand:
    for project in projects:
        if project.lower() == name.lower():
            return ParsedCommand(
                label=f"{project} in VS Code",
                project_name=project,
            )
    raise CommandTextError(f"No project called {name} on this PC")


def _parse_site(site: SearchSite, words: str) -> ParsedCommand:
    if not words:
        return ParsedCommand(label=site.label, url=site.home_url)
    if site.search_url is None:
        raise CommandTextError(f"{site.label} can't search yet, only open")
    return ParsedCommand(
        label=f"{site.label} search: {words}",
        url=site.search_url.format(words=quote_plus(words)),
    )


def _parse_app(name: str, apps: list[NodeApp]) -> ParsedCommand:
    lowered = name.lower()

    # An exact name wins over apps that only start with it.
    for app in apps:
        if app.name.lower() == lowered:
            return ParsedCommand(label=app.name, application_id=app.app_id)

    matches = [app for app in apps if app.name.lower().startswith(lowered)]

    if len(matches) == 1:
        return ParsedCommand(
            label=matches[0].name,
            application_id=matches[0].app_id,
        )
    if matches:
        names = ", ".join(app.name for app in matches[:MAX_CHOICES])
        raise CommandTextError(f"Which one: {names}?")
    # Maybe extra words ("spotify for me"): let the brain read the whole sentence.
    raise NotUnderstoodError(f"No app called {name} on this PC")


def _parse_url(text: str) -> ParsedCommand:
    url = _with_scheme(text)
    return ParsedCommand(label=url, url=url)


def _looks_like_url(text: str) -> bool:
    return "." in text and " " not in text


def _with_scheme(text: str) -> str:
    if text.lower().startswith(("http://", "https://")):
        return text
    return f"https://{text}"
