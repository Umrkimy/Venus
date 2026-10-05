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
from venus_node.voice.recorder import heard_speech, record_until_silence, trim_silence
from venus_node.voice.reporter import report_loop
from venus_node.voice.speakable import speakable
from venus_node.voice.status import IDLE, LISTENING, SLEEPING, SPEAKING, THINKING, Status, metered
from venus_node.voice.stop_words import (
    CANCEL,
    GOODBYE,
    MUTE,
    SLEEP,
    STOP_TALKING_PHRASES,
    control_word,
    resume_phrases,
)
from venus_node.voice.timing import Timer
from venus_node.voice.wake import WakeListener, grammar, wake_model_path
from venus_node.voice.wav import to_wav

RATE = 16000
FRAME = 1280  # 80 ms
# After Luna answers, how long Venus waits for your next sentence without
# "Hey Venus" (100 x 80 ms = 8 s). Quiet that long ends the conversation.
FOLLOW_UP_FRAMES = 100
# Ends the conversation: you said bye, cancelled, or nothing came through.
NOTHING = "nothing"
ENDS_CONVERSATION = {GOODBYE, CANCEL, NOTHING}


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


def watch_for_stop(stream, listener: WakeListener, stop: Event, done: Event) -> None:
    """Listen for "stop venus" while Luna thinks and talks."""
    listener.reset()
    while not done.is_set() and not stop.is_set():
        frame, _overflowed = stream.read(FRAME)
        if listener.heard(frame[:, 0]):
            print("Stopped by voice.")
            stop.set()


def answer(
    settings: NodeSettings,
    voice: VoiceChat,
    pcm: bytes,
    stream,
    status: Status | None = None,
    timer: Timer | None = None,
    stop_listener: WakeListener | None = None,
) -> str | None:
    """Text from the recording, Luna's reply, then her voice.

    Returns SLEEP when you asked Venus to stop listening, MUTE to mute the mic,
    GOODBYE / CANCEL / NOTHING when the conversation should end.
    With `stop_listener`, the mic stays on to hear "stop venus"; without it,
    the mic is off while she talks (or it would hear her and wake).
    """
    status = status or Status()
    timer = timer or Timer()
    status.stop.clear()  # A stop from before this turn doesn't count.
    status.set(THINKING)
    done = Event()
    watcher = None
    if stop_listener is not None:
        watcher = threading.Thread(
            target=watch_for_stop, args=(stream, stop_listener, status.stop, done), daemon=True,
        )
        watcher.start()
    try:
        return speak_reply(settings, voice, pcm, stream, status, timer, stop_listener is None)
    finally:
        done.set()
        # Two threads must never read the mic at once: wait for its last frame.
        if watcher is not None:
            watcher.join(timeout=1)


def speak_reply(
    settings: NodeSettings,
    voice: VoiceChat,
    pcm: bytes,
    stream,
    status: Status,
    timer: Timer,
    mic_off_while_speaking: bool,
) -> str | None:
    try:
        text = transcribe(settings, to_wav(trim_silence(pcm), RATE))
        timer.lap("transcribe")
        print("You said:", text or "(nothing)")
        if not text:
            return NOTHING
        # Checked here, before Luna: free, instant, works with Core's LLM down.
        word = control_word(text, settings.wake_phrases)
        if word == CANCEL:
            print("Cancelled.")
            return CANCEL
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
        return NOTHING
    if not reply:
        return None
    # "Goodbye": Luna still says bye back, then the conversation ends.
    outcome = GOODBYE if word == GOODBYE else None
    if status.stop.is_set():
        print("Stopped before Luna spoke.")
        return outcome

    def started() -> None:
        timer.lap("voice")  # Wait until her first sound.
        status.set(SPEAKING, reply)  # Her line shows as a subtitle while she talks.

    # The mic would hear her through the speakers ("...venus...") and wake.
    if mic_off_while_speaking:
        stream.stop()
    try:
        rate, pieces = speak_stream(settings, speakable(reply))
        play_pcm(pieces, rate, on_start=started, stop=status.stop)
        timer.lap("playback")
    except (OSError, HTTPException) as exc:
        # HTTPException: the stream broke halfway (Core restarted, Wi-Fi dropped).
        print("Luna's voice isn't available:", exc)
    finally:
        if mic_off_while_speaking:
            stream.start()
    return outcome


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
    stopper: WakeListener | None = None,
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
            hear(settings, voice, listener, resume, status, stream, muted, mute, stopper)


def hear(
    settings: NodeSettings,
    voice: VoiceChat,
    listener: WakeListener,
    resume: WakeListener,
    status: Status,
    stream,
    muted: Event,
    mute: Callable[[], None] | None = None,
    stopper: WakeListener | None = None,
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
    paused = False  # A Venus tab in front listens with the browser mic instead.
    dim_frames = 0  # How much longer the dim "sleeping" circle shows.
    for frame in frames:
        if muted.is_set() or status.closed:
            status.set(IDLE)
            return
        if status.web_listening:
            # Both mics would hear you and Venus would answer twice.
            paused = True
            continue
        if paused:
            paused = False
            listener.reset()
            recent.clear()
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
            outcome = answer(settings, voice, pcm, stream, status, timer, stopper)
            print(timer.report())
            # A conversation: keep listening without "Hey Venus" until you
            # say bye or stop, or go quiet.
            while outcome is None and not (muted.is_set() or status.closed or status.web_listening):
                status.set(LISTENING)
                timer = Timer()
                pcm = record_until_silence(
                    frames, start_frames=FOLLOW_UP_FRAMES, max_frames=FOLLOW_UP_FRAMES + 125,
                )
                timer.lap("record")
                if not heard_speech(pcm):
                    # Free: silence never goes to Core.
                    print(f"Quiet, so the conversation ended. Say {settings.wake_phrases[0]} to talk again.")
                    break
                outcome = answer(settings, voice, pcm, stream, status, timer, stopper)
                print(timer.report())
            if outcome in ENDS_CONVERSATION:
                print("Conversation ended.")
        finally:
            status.set(IDLE)
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


def wake_listeners(
    env_file: Path, settings: NodeSettings,
) -> tuple[WakeListener, WakeListener, WakeListener] | None:
    """The "Hey Venus", "start listening" and "stop venus" listeners, or None without a model."""
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
    # A third one, free on the same model: "stop venus" while she talks.
    stopper = WakeListener(
        vosk.KaldiRecognizer(model, RATE, grammar(STOP_TALKING_PHRASES)), STOP_TALKING_PHRASES,
    )
    return listener, resume, stopper


def start_listening(
    settings: NodeSettings,
    listener: WakeListener,
    resume: WakeListener,
    stopper: WakeListener,
    status: Status,
    muted: Event | None = None,
    mute: Callable[[], None] | None = None,
) -> threading.Thread:
    def loop() -> None:
        try:
            listen_loop(settings, listener, resume, status, muted, mute=mute, stopper=stopper)
        finally:
            # A mic error ends the loop; take the circle down with it.
            status.close()

    # The window must own the main thread, so the mic loop runs beside it.
    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    # The web's orb follows this one through Core.
    threading.Thread(target=report_loop, args=(settings, status, muted), daemon=True).start()
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
