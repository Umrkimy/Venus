import json
import signal
from http.client import HTTPException
import threading
import time
from collections import deque
from collections.abc import Callable, Iterator
from functools import partial
from pathlib import Path
from threading import Event
from urllib.error import HTTPError

import numpy as np

from venus_node.config import NodeSettings, load_settings
from venus_node.voice.conversation import VoiceChat
from venus_node.voice.core_client import chat, speak_stream, transcribe
from venus_node.voice.player import play_pcm
from venus_node.voice.recorder import record_until_silence, trim_silence
from venus_node.voice.speakable import speakable
from venus_node.voice.status import IDLE, LISTENING, SLEEPING, SPEAKING, THINKING, Status, metered
from venus_node.voice.stop_words import CANCEL, MUTE, SLEEP, control_word, resume_phrases
from venus_node.voice.timing import Timer
from venus_node.voice.wake import WakeListener, grammar, wake_model_path
from venus_node.voice.wav import to_wav

RATE = 16000
FRAME = 1280  # 80 ms


def mic_frames(stream) -> Iterator[np.ndarray]:
    # One shared stream: the wake check and the recorder read the same frames.
    while True:
        frame, _overflowed = stream.read(FRAME)
        yield frame[:, 0]


def problem(exc: OSError) -> str:
    if isinstance(exc, HTTPError) and exc.code == 409:
        return "Venus isn't connected to this PC. Run start-venus.cmd first."
    if isinstance(exc, HTTPError) and exc.code == 422:
        # Core's own words, e.g. "I couldn't hear anything. Check your mic..."
        try:
            return json.loads(exc.read())["detail"]
        except (ValueError, KeyError, TypeError):
            pass
    return f"Couldn't reach Core: {exc}"


def answer(
    settings: NodeSettings,
    voice: VoiceChat,
    pcm: bytes,
    stream,
    status: Status | None = None,
    timer: Timer | None = None,
) -> str | None:
    """Text from the recording, Luna's reply, then her voice.

    Returns SLEEP when you asked Venus to stop listening, MUTE to mute the mic.
    """
    status = status or Status()
    timer = timer or Timer()
    status.set(THINKING)
    try:
        text = transcribe(settings, to_wav(trim_silence(pcm), RATE))
        timer.lap("transcribe")
        print("You said:", text or "(nothing)")
        if not text:
            return None
        # Checked here, before Luna: free, instant, works with Core's LLM down.
        word = control_word(text, settings.wake_phrases)
        if word == CANCEL:
            print("Cancelled.")
            return None
        if word == SLEEP:
            print(f"Sleeping. Say \"{resume_phrases(settings.wake_phrases)[0]}\" to wake me.")
            return SLEEP
        if word == MUTE:
            print("Muting the mic. Unmute from the tray icon.")
            return MUTE
        reply = voice.ask(text)
        timer.lap("chat")
        print("Luna:", reply)
    except OSError as exc:
        print(problem(exc))
        return None
    if not reply:
        return None

    def started() -> None:
        timer.lap("voice")  # Wait until her first sound.
        status.set(SPEAKING)

    # The mic would hear her through the speakers ("...venus...") and wake.
    stream.stop()
    try:
        rate, pieces = speak_stream(settings, speakable(reply))
        play_pcm(pieces, rate, on_start=started)
        timer.lap("playback")
    except (OSError, HTTPException) as exc:
        # HTTPException: the stream broke halfway (Core restarted, Wi-Fi dropped).
        print("Luna's voice isn't available:", exc)
    finally:
        stream.start()
    return None


def find_mic(name: str, devices: list[dict]) -> int | None:
    """Index of the first input device whose name contains `name`, or None for the default."""
    if not name:
        return None
    for index, device in enumerate(devices):
        if device["max_input_channels"] > 0 and name.lower() in device["name"].lower():
            return index
    print(f'No mic named "{name}"; using the Windows default mic.')
    return None


def open_mic(name: str = ""):
    # Imported here so tests and the connect command don't need a mic.
    import sounddevice as sd

    device = find_mic(name, list(sd.query_devices()))
    return sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME, device=device)


def listen_loop(
    settings: NodeSettings,
    listener: WakeListener,
    resume: WakeListener,
    status: Status,
    muted: Event | None = None,
    open_stream: Callable | None = None,
    mute: Callable[[], None] | None = None,
) -> None:
    muted = muted if muted is not None else Event()
    open_stream = open_stream or partial(open_mic, settings.mic)
    voice = VoiceChat(partial(chat, settings))
    while not status.closed:
        if muted.is_set():
            # Mic closed while muted, so Windows' mic light goes off too.
            time.sleep(0.2)
            continue
        with open_stream() as stream:
            hear(settings, voice, listener, resume, status, stream, muted, mute)


def hear(
    settings: NodeSettings,
    voice: VoiceChat,
    listener: WakeListener,
    resume: WakeListener,
    status: Status,
    stream,
    muted: Event,
    mute: Callable[[], None] | None = None,
) -> None:
    """Wake, record, answer, until muted or closed.

    `mute` is the tray's Mute mic; without a tray (dev window) "mute" sleeps instead.
    """
    # The frames while the phrase was holding may already have "open ..." in them.
    recent: deque[np.ndarray] = deque(maxlen=5)
    frames = metered(mic_frames(stream), status)
    listener.reset()
    resume.reset()
    print(f"Say {' / '.join(settings.wake_phrases)}... (Ctrl+C to stop)")
    asleep = False
    dim_frames = 0  # How much longer the dim "sleeping" circle shows.
    for frame in frames:
        if muted.is_set() or status.closed:
            status.set(IDLE)
            return
        recent.append(frame)
        if dim_frames:
            dim_frames -= 1
            if dim_frames == 0:
                status.set(IDLE)
        if asleep:
            # Asleep: only the local "start listening" check runs, nothing goes to Core.
            if resume.heard(frame):
                asleep = False
                resume.reset()
                listener.reset()
                print("Listening again.")
            continue
        if not listener.heard(frame):
            continue
        print("Listening...")
        status.set(LISTENING)
        timer = Timer()
        try:
            pcm = b"".join(f.tobytes() for f in recent) + record_until_silence(frames)
            timer.lap("record")
            outcome = answer(settings, voice, pcm, stream, status, timer)
        finally:
            status.set(IDLE)
            print(timer.report())
        if outcome == MUTE and mute is not None:
            mute()
            status.set(IDLE)
            return
        if outcome in (SLEEP, MUTE):
            asleep = True
            status.set(SLEEPING)
            dim_frames = 15  # About 1.2 s.
            resume.reset()
        listener.reset()
        recent.clear()


def wake_listeners(env_file: Path, settings: NodeSettings) -> tuple[WakeListener, WakeListener] | None:
    """The "Hey Venus" listener and the "start listening" one, or None without a model."""
    import vosk

    path = wake_model_path(env_file.parent, settings.wake_model)
    if not path.is_dir():
        print(f"No Vosk model at {path}. Set VENUS_NODE_WAKE_MODEL.")
        return None
    vosk.SetLogLevel(-1)
    model = vosk.Model(str(path))
    recognizer = vosk.KaldiRecognizer(model, RATE, grammar(settings.wake_phrases))
    listener = WakeListener(recognizer, settings.wake_phrases)
    # A second recognizer on the same model hears only "<wake phrase> start listening".
    wake_up = resume_phrases(settings.wake_phrases)
    resume = WakeListener(vosk.KaldiRecognizer(model, RATE, grammar(wake_up)), wake_up)
    return listener, resume


def start_listening(
    settings: NodeSettings,
    listener: WakeListener,
    resume: WakeListener,
    status: Status,
    muted: Event | None = None,
    mute: Callable[[], None] | None = None,
) -> threading.Thread:
    def loop() -> None:
        try:
            listen_loop(settings, listener, resume, status, muted, mute=mute)
        finally:
            # A mic error ends the loop; take the circle down with it.
            status.close()

    # The window must own the main thread, so the mic loop runs beside it.
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread


def run_listen(env_file: Path) -> None:
    from venus_node.voice.circle import Circle

    settings = load_settings(env_file)
    listeners = wake_listeners(env_file, settings)
    if listeners is None:
        return
    status = Status()
    start_listening(settings, *listeners, status)
    # Ctrl+C would be swallowed by the window loop; ask it to close instead.
    signal.signal(signal.SIGINT, lambda signum, frame: status.close())
    Circle(status).run()


def main() -> None:
    from venus_node.app.single import LISTENER, already_running_message, claim

    if not claim(LISTENER):
        print(already_running_message("Listening"))
        return
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_listen(node_directory / ".env")


if __name__ == "__main__":
    main()
