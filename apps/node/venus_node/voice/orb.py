import math
from typing import NamedTuple

import numpy as np

from venus_node.voice.status import LISTENING, SLEEPING, SPEAKING, THINKING

SIZE = 112
COUNT = 1500
# Screen top to bottom, like the reference: cool blue, purple, pink, warm orange.
GRADIENT = np.array(
    [[90, 150, 255], [150, 80, 220], [240, 60, 130], [255, 150, 70]], dtype=np.float64
)


class Motion(NamedTuple):
    spin: float  # Turns per second around the vertical axis.
    wobble: float  # How far the surface ripples out (fraction of the radius).
    scale: float  # Size of the sphere (fraction of the window).
    glow: float  # Overall brightness.


def motion(state: str, level: float, seconds: float) -> Motion | None:
    """How the orb moves in each state; None means hidden."""
    if state == LISTENING:
        # Your voice makes the surface ripple and the orb swell a little.
        # Quiet = small and calm, loud = big and rippling.
        return Motion(0.08, 0.04 + 0.12 * level, 0.25 + 0.14 * level, 0.8 + 0.2 * level)
    if state == THINKING:
        return Motion(0.35, 0.08, 0.34, 0.9)
    if state == SPEAKING:
        beat = abs(math.sin(2 * math.pi * 2 * seconds))
        return Motion(0.1, 0.06 + 0.08 * beat, 0.35, 1.0)
    if state == SLEEPING:
        return Motion(0.03, 0.02, 0.22, 0.45)
    return None


def sphere_points(count: int) -> np.ndarray:
    """Evenly spread points on a unit sphere (Fibonacci spiral)."""
    i = np.arange(count) + 0.5
    y = 1 - 2 * i / count
    ring = np.sqrt(1 - y * y)
    angle = math.pi * (3 - math.sqrt(5)) * i
    return np.stack([ring * np.cos(angle), y, ring * np.sin(angle)], axis=1)


def blur(image: np.ndarray) -> np.ndarray:
    """Cheap soft blur: average each pixel with its neighbours, twice."""
    for _ in range(2):
        image = (
            image
            + np.roll(image, 1, 0) + np.roll(image, -1, 0)
            + np.roll(image, 1, 1) + np.roll(image, -1, 1)
        ) / 5
    return image


class Orb:
    """Draws one frame of the glowing particle sphere."""

    def __init__(self, size: int = SIZE, count: int = COUNT) -> None:
        self.size = size
        self.points = sphere_points(count)
        # A few points sparkle white, like the stars in the reference.
        self.sparkle = np.random.default_rng(7).random(count) < 0.03

    def frame(self, state: str, level: float, seconds: float) -> np.ndarray:
        """BGRA pixels with premultiplied alpha, ready for UpdateLayeredWindow."""
        out = np.zeros((self.size, self.size, 4), dtype=np.uint8)
        m = motion(state, level, seconds)
        if m is None:
            return out
        x, y, z = self.points.T
        # Ripples: waves over the surface that drift with time.
        bump = (
            np.sin(3 * x + 2.1 * seconds)
            * np.sin(4 * y + 1.7 * seconds)
            * np.sin(5 * z + 2.6 * seconds)
        )
        r = 1 + m.wobble * bump
        # Spin around the vertical axis, then tilt toward the viewer.
        a = 2 * math.pi * m.spin * seconds
        x, z = x * math.cos(a) + z * math.sin(a), -x * math.sin(a) + z * math.cos(a)
        tilt = 0.35
        y, z = y * math.cos(tilt) - z * math.sin(tilt), y * math.sin(tilt) + z * math.cos(tilt)
        x, y, z = x * r, y * r, z * r

        half = self.size / 2
        radius = self.size * m.scale
        px = np.clip((half + x * radius).astype(int), 0, self.size - 1)
        py = np.clip((half - y * radius).astype(int), 0, self.size - 1)

        # Front points brighter, and the rim brightest (it reads as a glowing edge).
        depth = (np.clip(z, -1, 1) + 1) / 2
        rim = 1 - np.abs(np.clip(z, -1, 1))
        bright = (0.25 + 0.5 * depth) * (0.5 + 0.9 * rim) * m.glow

        where = py / (self.size - 1) * (len(GRADIENT) - 1)
        low = np.floor(where).astype(int).clip(0, len(GRADIENT) - 2)
        mix = (where - low)[:, None]
        color = GRADIENT[low] * (1 - mix) + GRADIENT[low + 1] * mix
        color[self.sparkle] = [255, 245, 250]
        color *= bright[:, None]

        canvas = np.zeros((self.size, self.size, 3))
        np.add.at(canvas, (py, px), color)
        canvas = canvas + 1.5 * blur(canvas)  # Sharp dots plus a soft halo.
        canvas = np.clip(canvas, 0, 255)

        # Brightness becomes opacity, so the glow fades into whatever is behind.
        # A soft dark core keeps the orb readable over light windows too.
        yy, xx = np.mgrid[0:self.size, 0:self.size]
        distance = np.hypot(xx - half, yy - half) / radius
        core = 235 * np.clip((1.08 - distance) / 0.3, 0, 1) * min(m.glow * 1.1, 1.0)
        alpha = np.maximum(canvas.max(axis=2), core)
        out[..., 0] = canvas[..., 2]  # Windows wants blue, green, red, alpha.
        out[..., 1] = canvas[..., 1]
        out[..., 2] = canvas[..., 0]
        out[..., 3] = alpha
        return out
