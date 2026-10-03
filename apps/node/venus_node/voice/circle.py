import ctypes
import time
import tkinter as tk
from ctypes import wintypes

import numpy as np

from venus_node.voice.orb import SIZE, Orb
from venus_node.voice.status import IDLE, Status

TICK_MS = 33  # About 30 frames a second.
MARGIN = 16  # Gap to the screen corner.

GWL_EXSTYLE = -20
WS_EX_LAYERED = 0x80000  # Per-pixel see-through.
WS_EX_TRANSPARENT = 0x20  # Clicks go to whatever is under the orb.
WS_EX_TOOLWINDOW = 0x80  # No taskbar button.
WS_EX_NOACTIVATE = 0x08000000  # Never steals focus from a game.
ULW_ALPHA = 2
AC_SRC_ALPHA = 1
SPI_GETWORKAREA = 0x30


class BLENDFUNCTION(ctypes.Structure):
    _fields_ = [
        ("BlendOp", ctypes.c_ubyte),
        ("BlendFlags", ctypes.c_ubyte),
        ("SourceConstantAlpha", ctypes.c_ubyte),
        ("AlphaFormat", ctypes.c_ubyte),
    ]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]


def windows_api():
    """user32/gdi32 with types set, so 64-bit handles aren't cut in half."""
    user32 = ctypes.WinDLL("user32")
    gdi32 = ctypes.WinDLL("gdi32")
    user32.GetParent.restype = wintypes.HWND
    user32.GetParent.argtypes = [wintypes.HWND]
    user32.GetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.SetWindowLongW.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.LONG]
    user32.GetDC.restype = wintypes.HDC
    user32.GetDC.argtypes = [wintypes.HWND]
    user32.SystemParametersInfoW.argtypes = [wintypes.UINT, wintypes.UINT, ctypes.c_void_p, wintypes.UINT]
    user32.UpdateLayeredWindow.argtypes = [
        wintypes.HWND, wintypes.HDC, ctypes.POINTER(wintypes.POINT), ctypes.POINTER(wintypes.SIZE),
        wintypes.HDC, ctypes.POINTER(wintypes.POINT), wintypes.DWORD,
        ctypes.POINTER(BLENDFUNCTION), wintypes.DWORD,
    ]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateDIBSection.restype = wintypes.HBITMAP
    gdi32.CreateDIBSection.argtypes = [
        wintypes.HDC, ctypes.POINTER(BITMAPINFOHEADER), wintypes.UINT,
        ctypes.POINTER(ctypes.c_void_p), wintypes.HANDLE, wintypes.DWORD,
    ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    return user32, gdi32


class Circle:
    """Glowing orb in the bottom-right corner that shows the Status."""

    def __init__(self, status: Status) -> None:
        self.status = status
        self.orb = Orb()
        self.user32, gdi32 = windows_api()

        self.root = tk.Tk()
        self.root.overrideredirect(True)  # No title bar or border.
        self.root.attributes("-topmost", True)
        # Bottom-right of the work area: the screen minus the taskbar.
        area = wintypes.RECT()
        self.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(area), 0)
        self.position = wintypes.POINT(area.right - SIZE - MARGIN, area.bottom - SIZE - MARGIN)
        self.root.geometry(f"{SIZE}x{SIZE}+{self.position.x}+{self.position.y}")
        self.root.update_idletasks()

        self.hwnd = self.user32.GetParent(self.root.winfo_id())
        style = self.user32.GetWindowLongW(self.hwnd, GWL_EXSTYLE)
        self.user32.SetWindowLongW(
            self.hwnd, GWL_EXSTYLE,
            style | WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE,
        )

        # One off-screen bitmap we copy each numpy frame into.
        self.screen_dc = self.user32.GetDC(None)
        self.memory_dc = gdi32.CreateCompatibleDC(self.screen_dc)
        header = BITMAPINFOHEADER(
            biSize=ctypes.sizeof(BITMAPINFOHEADER), biWidth=SIZE, biHeight=-SIZE,  # Top row first.
            biPlanes=1, biBitCount=32, biCompression=0,
        )
        self.bits = ctypes.c_void_p()
        bitmap = gdi32.CreateDIBSection(self.memory_dc, ctypes.byref(header), 0, ctypes.byref(self.bits), None, 0)
        gdi32.SelectObject(self.memory_dc, bitmap)

        self.start = time.monotonic()
        self.shown = 0.0  # Fades between 0 (hidden) and 1.
        self.last_state = IDLE
        self.show(np.zeros((SIZE, SIZE, 4), dtype=np.uint8))

    def show(self, pixels: np.ndarray) -> None:
        ctypes.memmove(self.bits, pixels.ctypes.data, pixels.nbytes)
        blend = BLENDFUNCTION(0, 0, 255, AC_SRC_ALPHA)
        self.user32.UpdateLayeredWindow(
            self.hwnd, self.screen_dc, ctypes.byref(self.position), ctypes.byref(wintypes.SIZE(SIZE, SIZE)),
            self.memory_dc, ctypes.byref(wintypes.POINT(0, 0)), 0, ctypes.byref(blend), ULW_ALPHA,
        )

    def draw(self) -> None:
        state, level = self.status.snapshot()
        if state != IDLE:
            self.last_state = state
        target = 0.0 if state == IDLE else 1.0
        if self.shown == 0.0 and target == 0.0:
            return  # Already hidden: nothing to redraw.
        self.shown += (target - self.shown) * 0.25
        if self.shown < 0.02 and target == 0.0:
            self.shown = 0.0
            self.show(np.zeros((SIZE, SIZE, 4), dtype=np.uint8))
            return
        # While fading out keep drawing the last state, just dimmer.
        pixels = self.orb.frame(self.last_state, level, time.monotonic() - self.start)
        if self.shown < 1.0:
            pixels = (pixels * self.shown).astype(np.uint8)
        self.show(np.ascontiguousarray(pixels))

    def tick(self) -> None:
        if self.status.closed:
            self.root.destroy()
            return
        self.draw()
        self.root.after(TICK_MS, self.tick)

    def run(self) -> None:
        self.tick()
        self.root.mainloop()
