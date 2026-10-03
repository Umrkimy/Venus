from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from openai import OpenAIError

from features.auth.dependencies import require_owner
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.repository import ShortcutRepository
from features.voice.dependencies import get_transcriber
from features.voice.sound_alike import fix_keywords
from features.voice.transcriber import Transcriber

# Minutes of speech fit easily; stops a huge upload from running up a bill.
MAX_AUDIO_BYTES = 10 * 1024 * 1024

router = APIRouter(prefix="/voice", dependencies=[Depends(require_owner)])


@router.post("/transcribe")
async def transcribe(
    request: Request,
    transcriber: Annotated[Transcriber, Depends(get_transcriber)],
    shortcuts: Annotated[ShortcutRepository, Depends(get_shortcut_repository)],
):
    # The browser sends the recording itself as the body, e.g. audio/webm.
    audio = await request.body()
    if not audio:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="No audio",
        )
    if len(audio) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Recording is too long",
        )

    content_type = request.headers.get("content-type", "audio/webm")
    keywords = [shortcut.keyword for shortcut in shortcuts.list_all()]
    hint = ", ".join(["Venus"] + keywords)
    try:
        text = await transcriber.transcribe(audio, content_type, hint)
    except OpenAIError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't hear that",
        ) from exc
    # "comics" and "comix" sound the same; the owner meant the shortcut.
    return {"text": fix_keywords(text, keywords)}
