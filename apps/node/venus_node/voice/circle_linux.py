import sys
import time
import tkinter as tk

import numpy as np
from PIL import Image, ImageTk

from venus_node.voice.corner import MARGIN, TEXT_WIDTH, TICK_MS, WIDTH
from venus_node.voice.orb import SIZE, Orb
from venus_node.voice.status import IDLE, LISTENING, SPEAKING, Status
from venus_node.voice.subtitle import subtitle_pixels

# Room for a bottom panel (KDE and GNOME docks are about this tall).
PANEL = 48
# Linux windows can't be see-through per pixel from tkinter, so the orb sits
# on a dark square that is only shown while Venus listens, thinks or talks.
BACKGROUND = (12, 10, 18)
OPACITY = 0.92


def to_rgb(pixels: np.ndarray) -> np.ndarray:
    """Premultiplied BGRA (the Windows layout the orb draws) over the dark background."""
    alpha = pixels[..., 3:4].astype(np.float32) / 255
    rgb = pixels[..., 2::-1].astype(np.float32)  # Blue, green, red -> red, green, blue.
    out = rgb + np.array(BACKGROUND, dtype=np.float32) * (1 - alpha)
    return np.clip(out, 0, 255).astype(np.uint8)


def hide_dock_icon() -> None:
    """On a Mac, Venus lives in the menu bar: no Dock icon for the orb window."""
    if sys.platform != "darwin":
        return
    try:
        import AppKit  # From pyobjc, which the Mac tray icon (pystray) needs anyway.

        AppKit.NSApplication.sharedApplication().setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
    except Exception:
        pass  # Only cosmetic.


class Circle:
    """The orb and subtitles in the bottom-right corner, Linux and Mac version.

    Same look and timing as the Windows one (voice/circle.py). It hides
    completely when idle or while a Venus tab is in front, so the dark
    square never covers your screen for long.
    """

    def __init__(self, status: Status) -> None:
        self.status = status
        self.orb = Orb()
        self.root = tk.Tk()
        self.root.overrideredirect(True)  # No title bar or border.
        self.root.attributes("-topmost", True)
        try:
            self.root.attributes("-type", "splash")  # No taskbar button on X11.
        except tk.TclError:
            pass  # Only X11 knows this one (not Wayland-only or a Mac).
        try:
            self.root.attributes("-alpha", OPACITY)
        except tk.TclError:
            pass
        hide_dock_icon()
        x = self.root.winfo_screenwidth() - WIDTH - MARGIN
        y = self.root.winfo_screenheight() - SIZE - MARGIN - PANEL
        self.root.geometry(f"{WIDTH}x{SIZE}+{x}+{y}")
        self.label = tk.Label(self.root, borderwidth=0, highlightthickness=0, bg="#%02x%02x%02x" % BACKGROUND)
        self.label.pack()
        self.photo = None  # Kept, or tkinter throws the picture away.
        self.root.withdraw()
        self.visible = False

        self.start = time.monotonic()
        self.shown = 0.0
        self.last_state = IDLE
        self.subtitle = ""
        self.subtitle_image = subtitle_pixels("", TEXT_WIDTH, SIZE)

    def show(self, pixels: np.ndarray | None) -> None:
        if pixels is None:
            if self.visible:
                self.root.withdraw()
                self.visible = False
            return
        self.photo = ImageTk.PhotoImage(Image.fromarray(to_rgb(pixels), "RGB"))
        self.label.configure(image=self.photo)
        if not self.visible:
            self.root.deiconify()
            self.visible = True

    def draw(self) -> None:
        state, level = self.status.snapshot()
        _, subtitle = self.status.report()
        if state != IDLE:
            self.last_state = state
            if subtitle != self.subtitle:
                self.subtitle = subtitle
                self.subtitle_image = subtitle_pixels(subtitle, TEXT_WIDTH, SIZE, newest=state == LISTENING)
        target = 0.0 if state == IDLE or self.status.web_watching else 1.0
        if self.shown == 0.0 and target == 0.0:
            return
        self.shown += (target - self.shown) * 0.25
        if self.shown < 0.02 and target == 0.0:
            self.shown = 0.0
            self.show(None)
            return
        pixels = np.zeros((SIZE, WIDTH, 4), dtype=np.uint8)
        pixels[:, WIDTH - SIZE:] = self.orb.frame(self.last_state, level, time.monotonic() - self.start)
        if self.last_state in (LISTENING, SPEAKING):
            pixels[:, :TEXT_WIDTH] = self.subtitle_image
        if self.shown < 1.0:
            pixels = (pixels * self.shown).astype(np.uint8)
        self.show(pixels)

    def tick(self) -> None:
        if self.status.closed:
            self.root.destroy()
            return
        self.draw()
        self.root.after(TICK_MS, self.tick)

    def run(self) -> None:
        self.tick()
        self.root.mainloop()
