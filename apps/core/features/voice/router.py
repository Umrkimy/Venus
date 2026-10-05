from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from openai import OpenAIError
from pydantic import BaseModel

from features.auth.dependencies import require_owner_or_node
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.repository import ShortcutRepository
from features.voice.dependencies import get_speaker, get_transcriber
from features.voice.sound_alike import fix_keywords
from features.voice.speaker import Speaker
from features.voice.transcriber import Transcriber, is_hint_echo

# Minutes of speech fit easily; stops a huge upload from running up a bill.
MAX_AUDIO_BYTES = 10 * 1024 * 1024

NOTHING_HEARD = "I couldn't hear anything. Check your mic is plugged in and not muted."

# Luna's lines are short; a runaway reply can't burn Fish credit.
MAX_SPEAK_CHARS = 1000

router = APIRouter(prefix="/voice", dependencies=[Depends(require_owner_or_node)])


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
    if is_hint_echo(text, hint):
        # Silence, not words: say so instead of typing the hint into the chat.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=NOTHING_HEARD,
        )
    # "comics" and "comix" sound the same; the owner meant the shortcut.
    return {"text": fix_keywords(text, keywords)}


class SpeakRequest(BaseModel):
    text: str


@router.post("/speak")
async def speak(
    body: SpeakRequest,
    speaker: Annotated[Speaker, Depends(get_speaker)],
):
    text = body.text.strip()
    if not text:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Nothing to say",
        )
    if len(text) > MAX_SPEAK_CHARS:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="Text is too long to speak",
        )

    try:
        audio = await speaker.speak(text)
    except httpx2.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't speak that",
        ) from exc
    return Response(content=audio, media_type="audio/mpeg")
