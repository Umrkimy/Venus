import signal
import threading
from collections import deque
from collections.abc import Iterator
from functools import partial
from pathlib import Path
from urllib.error import HTTPError

import numpy as np

from venus_node.config import NodeSettings, load_settings
from venus_node.voice.conversation import VoiceChat
from venus_node.voice.core_client import chat, speak, transcribe
from venus_node.voice.player import play_mp3
from venus_node.voice.recorder import record_until_silence
from venus_node.voice.speakable import speakable
from venus_node.voice.status import IDLE, LISTENING, SLEEPING, SPEAKING, THINKING, Status, metered
from venus_node.voice.stop_words import CANCEL, SLEEP, control_word, resume_phrases
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
    return f"Couldn't reach Core: {exc}"


def answer(
    settings: NodeSettings,
    voice: VoiceChat,
    pcm: bytes,
    stream,
    status: Status | None = None,
) -> str | None:
    """Text from the recording, Luna's reply, then her voice.

    Returns SLEEP when you asked Venus to stop listening.
    """
    status = status or Status()
    status.set(THINKING)
    try:
        text = transcribe(settings, to_wav(pcm, RATE))
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
        reply = voice.ask(text)
        print("Luna:", reply)
    except OSError as exc:
        print(problem(exc))
        return None
    if not reply:
        return None
    try:
        mp3 = speak(settings, speakable(reply))
    except OSError as exc:
        print("Luna's voice isn't available:", exc)
        return None
    # The mic would hear her through the speakers ("...venus...") and wake.
    stream.stop()
    status.set(SPEAKING)
    try:
        play_mp3(mp3)
    finally:
        stream.start()
    return None


def listen_loop(
    settings: NodeSettings,
    listener: WakeListener,
    resume: WakeListener,
    status: Status,
) -> None:
    # Imported here so tests and the connect command don't need a mic.
    import sounddevice as sd

    voice = VoiceChat(partial(chat, settings))
    # The frames while the phrase was holding may already have "open ..." in them.
    recent: deque[np.ndarray] = deque(maxlen=5)

    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME) as stream:
        frames = metered(mic_frames(stream), status)
        print(f"Say {' / '.join(settings.wake_phrases)}... (Ctrl+C to stop)")
        asleep = False
        dim_frames = 0  # How much longer the dim "sleeping" circle shows.
        for frame in frames:
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
            try:
                pcm = b"".join(f.tobytes() for f in recent) + record_until_silence(frames)
                outcome = answer(settings, voice, pcm, stream, status)
            finally:
                status.set(IDLE)
            if outcome == SLEEP:
                asleep = True
                status.set(SLEEPING)
                dim_frames = 15  # About 1.2 s.
                resume.reset()
            listener.reset()
            recent.clear()


def run_listen(env_file: Path) -> None:
    import vosk

    from venus_node.voice.circle import Circle

    settings = load_settings(env_file)
    path = wake_model_path(env_file.parent, settings.wake_model)
    if not path.is_dir():
        print(f"No Vosk model at {path}. Set VENUS_NODE_WAKE_MODEL.")
        return
    vosk.SetLogLevel(-1)
    model = vosk.Model(str(path))
    recognizer = vosk.KaldiRecognizer(model, RATE, grammar(settings.wake_phrases))
    listener = WakeListener(recognizer, settings.wake_phrases)
    # A second recognizer on the same model hears only "<wake phrase> start listening".
    wake_up = resume_phrases(settings.wake_phrases)
    resume = WakeListener(vosk.KaldiRecognizer(model, RATE, grammar(wake_up)), wake_up)
    status = Status()

    def loop() -> None:
        try:
            listen_loop(settings, listener, resume, status)
        finally:
            # A mic error ends the loop; take the circle down with it.
            status.close()

    # The window must own the main thread, so the mic loop runs beside it.
    threading.Thread(target=loop, daemon=True).start()
    # Ctrl+C would be swallowed by the window loop; ask it to close instead.
    signal.signal(signal.SIGINT, lambda signum, frame: status.close())
    Circle(status).run()


def main() -> None:
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_listen(node_directory / ".env")


if __name__ == "__main__":
    main()
