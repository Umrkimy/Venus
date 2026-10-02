from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status

from features.auth.dependencies import require_owner
from features.personalities.dependencies import get_personality_repository
from features.personalities.models.personality import Personality
from features.personalities.repository import PersonalityRepository
from features.personalities.schemas import PersonalityRequest, PersonalityUpdate


router = APIRouter(prefix="/personalities", dependencies=[Depends(require_owner)])


def personality_json(personality: Personality) -> dict:
    return {
        "id": str(personality.id),
        "name": personality.name,
        "text": personality.text,
        "active": personality.active,
        "updated_at": personality.updated_at.isoformat(),
    }


def personality_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Personality not found",
    )


@router.get("")
def list_personalities(
    personalities: Annotated[
        PersonalityRepository,
        Depends(get_personality_repository),
    ],
):
    return [personality_json(personality) for personality in personalities.list_all()]


@router.post("", status_code=status.HTTP_201_CREATED)
def create_personality(
    request: PersonalityRequest,
    personalities: Annotated[
        PersonalityRepository,
        Depends(get_personality_repository),
    ],
):
    return personality_json(personalities.create(request.name, request.text))


@router.patch("/{personality_id}")
def update_personality(
    personality_id: UUID,
    request: PersonalityUpdate,
    personalities: Annotated[
        PersonalityRepository,
        Depends(get_personality_repository),
    ],
):
    if personalities.get(personality_id) is None:
        raise personality_not_found()
    if request.name is not None or request.text is not None:
        personalities.update(personality_id, request.name, request.text)
    # Only switching on means something: another one must take over anyway.
    if request.active:
        personalities.activate(personality_id)
    return personality_json(personalities.get(personality_id))


@router.delete("/{personality_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_personality(
    personality_id: UUID,
    personalities: Annotated[
        PersonalityRepository,
        Depends(get_personality_repository),
    ],
):
    personality = personalities.get(personality_id)
    if personality is None:
        raise personality_not_found()
    if personality.active:
        # Venus always keeps one personality switched on.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Switch personality first",
        )
    personalities.delete(personality_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
