
"""gui/waveform.py — Real-time audio waveform display.

Shows a small always-on-top, borderless window at the top-centre of the
screen with vertical RMS bars that scroll right-to-left while recording.
The window pulls float levels from the recorder’s queue on every Tk
.after() tick (40 ms ≈ 25 fps) and redraws the canvas.
"""

from __future__ import annotations

import queue
import tkinter as tk
from collections import deque
from typing import Callable

from .ui import get as get_ui

# Visual constants
WIDTH = 360
HEIGHT = 80
BAR_WIDTH = 3
BAR_GAP = 1
BAR_COLOR = "#7fb1ff"     # Accent blue
BG_COLOR = "#101218"      # Near-black background


class WaveformWindow:
    """Small always-on-top window that draws live RMS bars while recording.

    Owns no audio thread — it pulls floats off the recorder's `levels` queue
    in the Tk thread via .after(). Open with `show()`, close with `hide()`.
    """

    def __init__(self, get_levels: Callable[[], queue.Queue[float]]) -> None:
        self._get_levels = get_levels
        self._win: tk.Toplevel | None = None
        self._canvas: tk.Canvas | None = None
        self._bars: deque[float] = deque(maxlen=WIDTH // (BAR_WIDTH + BAR_GAP))
        self._closed = True

    def show(self) -> None:
        get_ui().submit(self._open)

    def hide(self) -> None:
        get_ui().submit(self._close)

    def _open(self, root: tk.Tk) -> None:
        if self._win is not None:
            return
        win = tk.Toplevel(root)
        win.title("Voice Flow")
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.92)
        except tk.TclError:
            pass

        canvas = tk.Canvas(win, width=WIDTH, height=HEIGHT, bg=BG_COLOR, highlightthickness=0)
        canvas.pack()

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        x = (sw - WIDTH) // 2
        y = 24
        win.geometry(f"+{x}+{y}")

        self._win = win
        self._canvas = canvas
        self._bars.clear()
        self._closed = False
        self._tick(root)

    def _close(self, _root: tk.Tk) -> None:
        self._closed = True
        if self._win is not None:
            try:
                self._win.destroy()
            except tk.TclError:
                pass
        self._win = None
        self._canvas = None

    def _tick(self, root: tk.Tk) -> None:
        if self._closed or self._canvas is None or self._win is None:
            return
        levels_q = self._get_levels()
        try:
            while True:
                self._bars.append(levels_q.get_nowait())
        except queue.Empty:
            pass

        c = self._canvas
        c.delete("all")
        x = WIDTH - BAR_WIDTH
        for level in reversed(self._bars):
            h = max(2, int(level * (HEIGHT - 6)))
            y0 = (HEIGHT - h) // 2
            y1 = y0 + h
            c.create_rectangle(x, y0, x + BAR_WIDTH, y1, fill=BAR_COLOR, outline="")
            x -= BAR_WIDTH + BAR_GAP
            if x < 0:
                break

        try:
            self._win.after(40, lambda: self._tick(root))
        except tk.TclError:
            self._closed = True


