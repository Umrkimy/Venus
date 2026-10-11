from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status

from features.auth.dependencies import require_owner
from features.character.dependencies import get_character_repository
from features.character.repository import CharacterInfo, CharacterRepository, is_vrm

# VRoid models are usually 10-50 MB; this only stops a mistake (a video, say).
MAX_MODEL_BYTES = 100 * 1024 * 1024

router = APIRouter(prefix="/character", dependencies=[Depends(require_owner)])


def info_body(info: CharacterInfo | None) -> dict:
    if info is None:
        return {"custom": False}
    return {
        "custom": True,
        "name": info.name,
        "size": info.size,
        "uploaded_at": info.uploaded_at.isoformat(),
    }


def etag(info: CharacterInfo) -> str:
    # Changes with every upload, so the browser keeps its copy until then.
    return f'"{int(info.uploaded_at.timestamp() * 1000)}"'


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


@router.put("/model")
async def put_model(
    request: Request,
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
    name: Annotated[str, Query(min_length=1, max_length=200)],
):
    # The browser sends the file itself as the body.
    data = await request.body()
    if len(data) > MAX_MODEL_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Model is over 100 MB",
        )
    if not is_vrm(data):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="That isn't a .vrm model",
        )
    return info_body(character.save(name, data))


@router.delete("/model", status_code=status.HTTP_204_NO_CONTENT)
def delete_model(
    character: Annotated[CharacterRepository, Depends(get_character_repository)],
):
    character.delete()
