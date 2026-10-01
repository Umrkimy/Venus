from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from features.auth.dependencies import require_owner
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from features.shortcuts.schemas import (
    ShortcutFields,
    ShortcutRequest,
    ShortcutUpdate,
)
from features.shortcuts.search_template import (
    SearchTemplateError,
    search_template,
)


router = APIRouter(prefix="/shortcuts", dependencies=[Depends(require_owner)])


def shortcut_json(shortcut: SiteShortcut) -> dict:
    return {
        "keyword": shortcut.keyword,
        "label": shortcut.label,
        "home_url": shortcut.home_url,
        "search_url": shortcut.search_url,
    }


def search_url_from(request: ShortcutFields) -> str | None:
    if request.search_example is None:
        return None
    try:
        return search_template(str(request.search_example), request.search_words)
    except SearchTemplateError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error


@router.get("")
def list_shortcuts(
    shortcuts: Annotated[
        ShortcutRepository,
        Depends(get_shortcut_repository),
    ],
):
    return {"shortcuts": [shortcut_json(s) for s in shortcuts.list_all()]}


@router.post("", status_code=status.HTTP_201_CREATED)
def add_shortcut(
    request: ShortcutRequest,
    shortcuts: Annotated[
        ShortcutRepository,
        Depends(get_shortcut_repository),
    ],
):
    if shortcuts.get(request.keyword) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"You already have a shortcut called {request.keyword}",
        )

    shortcut = SiteShortcut(
        keyword=request.keyword,
        label=request.label,
        home_url=str(request.home_url),
        search_url=search_url_from(request),
    )
    shortcuts.add(shortcut)
    return shortcut_json(shortcut)


@router.put("/{keyword}")
def update_shortcut(
    keyword: str,
    request: ShortcutUpdate,
    shortcuts: Annotated[
        ShortcutRepository,
        Depends(get_shortcut_repository),
    ],
):
    shortcut = shortcuts.update(
        keyword.lower(),
        label=request.label,
        home_url=str(request.home_url),
        search_url=search_url_from(request),
    )
    if shortcut is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No shortcut called {keyword}",
        )
    return shortcut_json(shortcut)


@router.delete("/{keyword}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shortcut(
    keyword: str,
    shortcuts: Annotated[
        ShortcutRepository,
        Depends(get_shortcut_repository),
    ],
):
    if not shortcuts.delete(keyword.lower()):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No shortcut called {keyword}",
        )
