from collections import deque
from collections.abc import Iterator
from pathlib import Path

import numpy as np

from venus_node.config import load_settings
from venus_node.voice.core_client import transcribe
from venus_node.voice.recorder import record_until_silence
from venus_node.voice.wake import WakeListener, grammar, wake_model_path
from venus_node.voice.wav import to_wav

RATE = 16000
FRAME = 1280  # 80 ms


def mic_frames(stream) -> Iterator[np.ndarray]:
    # One shared stream: the wake check and the recorder read the same frames.
    while True:
        frame, _overflowed = stream.read(FRAME)
        yield frame[:, 0]


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
            try:
                print("You said:", transcribe(settings, to_wav(pcm, RATE)) or "(nothing)")
            except OSError as exc:
                print("Couldn't reach Core:", exc)
            listener.reset()
            recent.clear()


def main() -> None:
    node_directory = Path(__file__).resolve().parent.parent.parent
    run_listen(node_directory / ".env")


if __name__ == "__main__":
    main()
