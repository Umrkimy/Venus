from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from features.auth.dependencies import require_owner
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.models.site_shortcut import SiteShortcut
from features.shortcuts.repository import ShortcutRepository
from features.shortcuts.schemas import ShortcutRequest


router = APIRouter(prefix="/shortcuts", dependencies=[Depends(require_owner)])


def shortcut_json(shortcut: SiteShortcut) -> dict:
    return {
        "keyword": shortcut.keyword,
        "label": shortcut.label,
        "home_url": shortcut.home_url,
        "search_url": shortcut.search_url,
    }


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
        # str(None) would save the text "None", so keep None as None.
        search_url=str(request.search_url) if request.search_url else None,
    )
    shortcuts.add(shortcut)
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
