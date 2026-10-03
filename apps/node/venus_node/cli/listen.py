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


def answer(settings: NodeSettings, voice: VoiceChat, pcm: bytes, stream) -> None:
    """Text from the recording, Luna's reply, then her voice."""
    try:
        text = transcribe(settings, to_wav(pcm, RATE))
        print("You said:", text or "(nothing)")
        if not text:
            return
        reply = voice.ask(text)
        print("Luna:", reply)
    except OSError as exc:
        print(problem(exc))
        return
    if not reply:
        return
    try:
        mp3 = speak(settings, speakable(reply))
    except OSError as exc:
        print("Luna's voice isn't available:", exc)
        return
    # The mic would hear her through the speakers ("...venus...") and wake.
    stream.stop()
    try:
        play_mp3(mp3)
    finally:
        stream.start()


def run_listen(env_file: Path) -> None:
    # Imported here so tests and the connect command don't need a mic.
    import sounddevice as sd
    import vosk

    settings = load_settings(env_file)
    path = wake_model_path(env_file.parent, settings.wake_model)
    if not path.is_dir():
        print(f"No Vosk model at {path}. Set VENUS_NODE_WAKE_MODEL.")
        return
    vosk.SetLogLevel(-1)
    recognizer = vosk.KaldiRecognizer(vosk.Model(str(path)), RATE, grammar(settings.wake_phrases))
    listener = WakeListener(recognizer, settings.wake_phrases)
    voice = VoiceChat(partial(chat, settings))
    # The frames while the phrase was holding may already have "open ..." in them.
    recent: deque[np.ndarray] = deque(maxlen=5)

    with sd.InputStream(samplerate=RATE, channels=1, dtype="int16", blocksize=FRAME) as stream:
        frames = mic_frames(stream)
        print(f"Say {' / '.join(settings.wake_phrases)}... (Ctrl+C to stop)")
        for frame in frames:
            recent.append(frame)
            if not listener.heard(frame):
                continue
            print("Listening...")
            pcm = b"".join(f.tobytes() for f in recent) + record_until_silence(frames)
            answer(settings, voice, pcm, stream)
            listener.reset()
            recent.clear()


def main() -> None:
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_listen(node_directory / ".env")


if __name__ == "__main__":
    main()
