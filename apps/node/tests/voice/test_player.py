from venus_node.voice.player import even_pieces, play_pcm


def test_even_pieces_never_split_a_sample():
    assert list(even_pieces([b"abc", b"de", b"f"])) == [b"ab", b"cd", b"ef"]


class FakeSpeakers:
    def __init__(self, log):
        self.log = log

    def __enter__(self):
        self.log.append("open")
        return self

    def __exit__(self, *args):
        self.log.append("close")

    def write(self, data):
        self.log.append(data)


def test_play_pcm_writes_each_piece_and_says_when_sound_starts():
    log = []

    play_pcm(iter([b"ab", b"cd"]), 44100, on_start=lambda: log.append("start"), open_output=lambda: FakeSpeakers(log))

    assert log == ["open", "start", b"ab", b"cd", "close"]
