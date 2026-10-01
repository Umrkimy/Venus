from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    HttpUrl,
    StringConstraints,
    field_validator,
)


class ShortcutFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]
    home_url: HttpUrl
    # A real search link; the router turns it into a {words} template.
    search_example: HttpUrl | None = None
    search_words: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, max_length=100),
    ] = None


class ShortcutRequest(ShortcutFields):
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

    @field_validator("keyword")
    @classmethod
    def keyword_is_not_open(cls, keyword: str) -> str:
        # "open notepad" must still reach the app rules in the parser.
        if keyword == "open":
            raise ValueError("You can't name a shortcut open")
        return keyword


class ShortcutUpdate(ShortcutFields):
    pass
