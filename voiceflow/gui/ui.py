"""gui/ui.py — Dedicated Tk thread for all GUI operations.

Tkinter is not thread-safe: only the thread that created the Tk root
may interact with it.  This module creates exactly one hidden Tk root
on a daemon thread and exposes a submit() method that queues callables
for execution on that thread.

Every GUI module (settings, history, notify, waveform) calls
get_ui().submit(fn) instead of touching Tk directly.  The dispatcher
polls the queue every 40 ms via root.after().
"""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable


import queue
import tkinter as tk
from typing import Callable

class UIThread:
    """Single-threaded Tk dispatcher.
    On macOS, Tkinter must be initialized and run on the main thread.
    Call start() once; then use submit(fn) from any thread.
    main.py is responsible for calling get_ui()._root.mainloop() at the end.
    """
    def __init__(self) -> None:
        self._queue: queue.Queue[Callable[[tk.Tk], None]] = queue.Queue()
        self._root: tk.Tk | None = None

    def start(self) -> None:
        if self._root is not None:
            return
        root = tk.Tk()
        root.withdraw()
        self._root = root
        self._poll()

    def _poll(self) -> None:
        assert self._root is not None
        try:
            while True:
                fn = self._queue.get_nowait()
                try:
                    fn(self._root)
                except Exception as exc:  # noqa: BLE001
                    print(f"[ui] dispatch error: {exc}")
        except queue.Empty:
            pass
        self._root.after(40, self._poll)

    def submit(self, fn: Callable[[tk.Tk], None]) -> None:
        self._queue.put(fn)

_ui: UIThread | None = None

def get() -> UIThread:
    global _ui
    if _ui is None:
        _ui = UIThread()
        _ui.start()
    return _ui


