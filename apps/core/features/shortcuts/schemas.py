from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    field_validator,
)


class ShortcutRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # The pattern runs before to_lower, so capitals must pass it.
    keyword: Annotated[
        str,
        StringConstraints(
            strip_whitespace=True,
            to_lower=True,
            pattern=r"^[A-Za-z0-9-]+$",
            max_length=50,
        ),
    ]
    label: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    home_url: HttpUrl
    search_url: HttpUrl | None = None

    @field_validator("keyword")
    @classmethod
    def keyword_is_not_open(cls, keyword: str) -> str:
        # "open notepad" must still reach the app rules in the parser.
        if keyword == "open":
            raise ValueError("You can't name a shortcut open")
        return keyword

    @field_validator("search_url")
    @classmethod
    def search_url_has_words_slot(cls, url: HttpUrl | None) -> HttpUrl | None:
        if url is not None and "{words}" not in str(url):
            raise ValueError("The search link needs {words} where your search goes")
        return url
