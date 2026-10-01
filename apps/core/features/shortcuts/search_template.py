from urllib.parse import quote, quote_plus, urlsplit

# Names sites often give the search box in the link, e.g. ?q=naruto.
SEARCH_PARAMETERS = ("q", "query", "search", "keyword", "s", "term")


class SearchTemplateError(ValueError):
    pass


def search_template(link: str, words: str | None = None) -> str:
    if "{words}" in link:
        return link

    # Split by hand: parse_qsl would decode the other values (%3A becomes :).
    parts = urlsplit(link)
    pieces = parts.query.split("&")
    for position, piece in enumerate(pieces):
        name, _, _ = piece.partition("=")
        if name.lower() in SEARCH_PARAMETERS:
            pieces[position] = f"{name}={{words}}"
            return parts._replace(query="&".join(pieces)).geturl()

    # Search inside the path, e.g. /search/solo-leveling.
    if words:
        forms = (words, quote(words), quote_plus(words), words.replace(" ", "-"))
        for form in forms:
            index = link.lower().find(form.lower())
            if index != -1:
                return link[:index] + "{words}" + link[index + len(form):]

    raise SearchTemplateError(
        "I couldn't find your search in that link. What did you search for?"
    )
