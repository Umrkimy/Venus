from collections.abc import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_SIZE = 15
PADDING = 10
MAX_LINES = 3  # Three lines fit the orb's height; Luna's spoken lines are short.
BOX = (18, 14, 28, 210)  # Dark, mostly solid: readable over any window.
TEXT = (245, 240, 250, 255)


def load_font() -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.truetype("segoeui.ttf", FONT_SIZE)  # Windows' own UI font.
    except OSError:
        return ImageFont.load_default(FONT_SIZE)


def wrap(text: str, fits: Callable[[str], bool], max_lines: int = MAX_LINES) -> list[str]:
    """Split into lines that fit; cut with "..." past `max_lines`."""
    lines: list[str] = []
    for word in text.split():
        if lines and fits(f"{lines[-1]} {word}"):
            lines[-1] = f"{lines[-1]} {word}"
        else:
            lines.append(word)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = f"{lines[-1]}..."
    return lines


def subtitle_pixels(text: str, width: int, height: int, font=None) -> np.ndarray:
    """Luna's line in a dark box at the bottom right: premultiplied BGRA, like the orb."""
    font = font or load_font()
    image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    if text.strip():
        draw = ImageDraw.Draw(image)
        room = width - 2 * PADDING
        lines = wrap(text, lambda line: draw.textlength(line, font=font) <= room)
        line_height = FONT_SIZE + 5
        box_width = int(max(draw.textlength(line, font=font) for line in lines)) + 2 * PADDING
        box_height = len(lines) * line_height + 2 * PADDING - 4
        # Bottom-right, so it sits right next to the orb.
        left, top = width - box_width, height - box_height
        draw.rounded_rectangle((left, top, width - 1, height - 1), radius=10, fill=BOX)
        for row, line in enumerate(lines):
            draw.text((left + PADDING, top + PADDING - 3 + row * line_height), line, font=font, fill=TEXT)

    rgba = np.asarray(image, dtype=np.float64)
    alpha = rgba[..., 3:4] / 255
    out = np.empty((height, width, 4), dtype=np.uint8)
    out[..., :3] = (rgba[..., 2::-1] * alpha).astype(np.uint8)  # Blue, green, red, premultiplied.
    out[..., 3] = rgba[..., 3].astype(np.uint8)
    return out
