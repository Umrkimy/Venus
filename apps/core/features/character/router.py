from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel

from api.body_limit import read_body
from features.auth.dependencies import require_owner
from features.character.dependencies import get_animation_repository, get_character_repository
from features.character.repository import (
    AnimationInfo,
    AnimationRepository,
    CharacterInfo,
    CharacterRepository,
    is_vrm,
    is_vrma,
)

# VRoid models are usually 10-50 MB; this only stops a mistake (a video, say).
MAX_MODEL_BYTES = 100 * 1024 * 1024
# A move is usually well under 1 MB.
MAX_ANIMATION_BYTES = 20 * 1024 * 1024

# When an uploaded move plays: idle loops, hello once when she appears,
# the others while she listens, thinks or talks. FastAPI refuses anything else.
AnimationUse = Literal["idle", "hello", "listening", "thinking", "talking"]

router = APIRouter(prefix="/character", dependencies=[Depends(require_owner)])


def info_body(info: CharacterInfo | None) -> dict:
    if info is None:
        return {"custom": False}
    return {
        "custom": True,
        "id": info.id,
        "name": info.name,
        "size": info.size,
        "uploaded_at": info.uploaded_at.isoformat(),
    }


def model_body(info: CharacterInfo) -> dict:
    return {
        "id": info.id,
        "name": info.name,
        "size": info.size,
        "uploaded_at": info.uploaded_at.isoformat(),
        "active": info.active,
    }


def etag(info: CharacterInfo) -> str:
    # Changes when another model is put in use, so the browser keeps its copy until then.
    return f'"{info.id}-{int(info.uploaded_at.timestamp() * 1000)}"'


class ActiveModel(BaseModel):
    # None = the template.
    id: int | None


@router.get("")
def get_character(
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    return info_body(character.get_info())


@router.get("/model")
def get_model(
    request: Request,
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    info = character.get_info()
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No own model; use the template")
    # "no-cache" = keep it, but ask each time; unchanged costs a tiny 304, not megabytes.
    headers = {"ETag": etag(info), "Cache-Control": "private, no-cache"}
    if request.headers.get("if-none-match") == headers["ETag"]:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED, headers=headers)
    return Response(character.get_data(), media_type="model/gltf-binary", headers=headers)


@router.get("/models")
def list_models(
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    return [model_body(info) for info in character.list_info()]


@router.post("/models", status_code=status.HTTP_201_CREATED)
async def post_model(
    request: Request,
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
    name: Annotated[str, Query(min_length=1, max_length=200)],
):
    # The browser sends the file itself as the body.
    data = await read_body(request, MAX_MODEL_BYTES, "Model is over 100 MB")
    if not is_vrm(data):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That isn't a .vrm model",
        )
    return model_body(character.add(name, data))


@router.put("/active")
def put_active(
    choice: ActiveModel,
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    if not character.activate(choice.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such model")
    return info_body(character.get_info())


@router.delete("/models/{model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    model_id: int,
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    info = next((info for info in character.list_info() if info.id == model_id), None)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such model")
    # Like personalities: the one in use can't go, so Venus never loses her look by accident.
    if info.active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Switch to another model before deleting this one",
        )
    character.delete(model_id)


def animation_body(info: AnimationInfo) -> dict:
    return {
        "id": info.id,
        "name": info.name,
        "use": info.use,
        "size": info.size,
        "uploaded_at": info.uploaded_at.isoformat(),
    }


class AnimationChange(BaseModel):
    use: AnimationUse


@router.get("/animations")
def list_animations(
    animations: Annotated[AnimationRepository, Depends(get_animation_repository)],
):
    return [animation_body(info) for info in animations.list_info()]


@router.get("/animations/{animation_id}")
def get_animation(
    animation_id: int,
    animations: Annotated[AnimationRepository, Depends(get_animation_repository)],
):
    data = animations.get_data(animation_id)
    if data is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such animation")
    # A file never changes under its id (a new upload gets a new id), so the browser keeps it.
    headers = {"Cache-Control": "private, max-age=31536000, immutable"}
    return Response(data, media_type="model/gltf-binary", headers=headers)


@router.post("/animations", status_code=status.HTTP_201_CREATED)
async def post_animation(
    request: Request,
    animations: Annotated[AnimationRepository, Depends(get_animation_repository)],
    name: Annotated[str, Query(min_length=1, max_length=200)],
    use: AnimationUse = "idle",
):
    # The browser sends the file itself as the body.
    data = await read_body(request, MAX_ANIMATION_BYTES, "Animation is over 20 MB")
    if not is_vrma(data):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That isn't a .vrma animation",
        )
    return animation_body(animations.add(name, use, data))


@router.patch("/animations/{animation_id}")
def patch_animation(
    animation_id: int,
    change: AnimationChange,
    animations: Annotated[AnimationRepository, Depends(get_animation_repository)],
):
    info = animations.set_use(animation_id, change.use)
    if info is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such animation")
    return animation_body(info)


@router.delete("/animations/{animation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_animation(
    animation_id: int,
    animations: Annotated[AnimationRepository, Depends(get_animation_repository)],
):
    if not animations.delete(animation_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No such animation")
