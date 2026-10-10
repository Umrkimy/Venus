from typing import Annotated, Literal

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.responses import StreamingResponse
from openai import OpenAIError
from pydantic import BaseModel, Field

from features.auth.dependencies import require_owner_or_node
from features.settings.dependencies import get_settings_repository
from features.settings.repository import SettingsRepository
from features.shortcuts.dependencies import get_shortcut_repository
from features.shortcuts.repository import ShortcutRepository
from features.voice.dependencies import get_speaker, get_transcriber
from features.voice.live import LiveVoice, get_live_voice
from features.voice.sound_alike import fix_keywords
from features.voice.speaker import SAMPLE_RATE, Speaker
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


def checked_text(body: SpeakRequest) -> str:
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
    return text


@router.post("/speak")
async def speak(
    body: SpeakRequest,
    speaker: Annotated[Speaker, Depends(get_speaker)],
):
    text = checked_text(body)
    try:
        audio = await speaker.speak(text)
    except httpx2.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't speak that",
        ) from exc
    return Response(content=audio, media_type="audio/mpeg")


@router.post("/speak/stream")
async def speak_stream(
    body: SpeakRequest,
    speaker: Annotated[Speaker, Depends(get_speaker)],
):
    """Luna's voice as raw PCM pieces, so the PC starts playing before Fish is done."""
    chunks = speaker.stream(checked_text(body))
    try:
        # A Fish error (no credit, bad key) shows up before the first piece:
        # still time to answer 502 instead of a broken stream.
        first = await anext(chunks)
    except StopAsyncIteration:
        first = b""
    except httpx2.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Couldn't speak that",
        ) from exc

    async def audio():
        yield first
        async for chunk in chunks:
            yield chunk

    return StreamingResponse(
        audio(), media_type="audio/pcm", headers={"X-Sample-Rate": str(SAMPLE_RATE)},
    )


VoiceStateName = Literal["idle", "listening", "thinking", "speaking", "sleeping"]


class VoiceReport(BaseModel):
    state: VoiceStateName
    subtitle: str = Field(default="", max_length=MAX_SPEAK_CHARS)
    muted: bool = False


class VoiceReportReply(BaseModel):
    web_watching: bool
    web_listening: bool
    stop: bool
    # The Settings pause slider: the PC waits this long after you stop talking.
    end_pause_ms: int


class VoiceState(BaseModel):
    state: VoiceStateName
    subtitle: str
    muted: bool
    online: bool
    conversation_id: str | None


@router.put("/state")
async def report_state(
    body: VoiceReport,
    live: Annotated[LiveVoice, Depends(get_live_voice)],
    settings_repository: Annotated[SettingsRepository, Depends(get_settings_repository)],
) -> VoiceReportReply:
    """The PC's orb reports here. The answer says if a web tab shows the orb
    (and listens) instead, passes on the web's stop button and the pause setting."""
    reply = live.report(body.state, body.subtitle, body.muted)
    return VoiceReportReply(
        web_watching=reply.web_watching, web_listening=reply.web_listening, stop=reply.stop,
        end_pause_ms=settings_repository.get_end_pause_ms(),
    )


@router.get("/state")
async def watch_state(
    response: Response,
    live: Annotated[LiveVoice, Depends(get_live_voice)],
    listening: bool = False,
) -> VoiceState:
    """The web tab in front asks here; asking also hides the PC's orb for a moment.

    listening=true: the tab listens with the browser mic, so the PC pauses "Hey Venus".
    """
    response.headers["Cache-Control"] = "no-store"
    seen = live.watch(listening)
    return VoiceState(
        state=seen.state, subtitle=seen.subtitle, muted=seen.muted,
        online=seen.online, conversation_id=seen.conversation_id,
    )


@router.post("/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop(live: Annotated[LiveVoice, Depends(get_live_voice)]) -> None:
    """The web's stop button: Luna on the PC stops talking (or drops her answer)."""
    live.wish_stop()
