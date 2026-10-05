from venus_node.voice.subtitle import subtitle_pixels, wrap


def short(line: str) -> bool:
    return len(line) <= 10


def test_wrap_fills_lines_word_by_word():
    assert wrap("open spotify for me babe", short, max_lines=4) == ["open", "spotify", "for me", "babe"]


def test_wrap_cuts_long_lines_with_dots():
    lines = wrap("one two three four five six seven eight nine ten", short, max_lines=2)

    assert lines == ["one two", "three four..."]


def test_no_subtitle_is_fully_see_through():
    pixels = subtitle_pixels("", 300, 84)

    assert pixels.shape == (84, 300, 4)
    assert pixels.max() == 0


def test_subtitle_box_sits_bottom_right_and_is_premultiplied():
    pixels = subtitle_pixels("hi babe", 300, 84)

    alpha = pixels[..., 3]
    assert alpha[-5, -20] > 0  # Bottom right: next to the orb.
    assert alpha[5, 5] == 0  # Top left stays clear.
    # Premultiplied: no colour can be brighter than its own opacity.
    assert (pixels[..., :3].max(axis=2) <= alpha).all()
