"""gui/notify.py — Toast-style notification popup.

Displays a small borderless, semi-transparent overlay in the bottom-right
corner of the screen.  Auto-dismisses after a configurable duration.
Used to show the user their transcribed/refined text after pasting.
"""

from __future__ import annotations

import tkinter as tk

from .ui import get as get_ui

DEFAULT_DURATION_MS = 4000   # Auto-close after 4 seconds
MAX_PREVIEW_CHARS = 220      # Truncate long texts in the toast


def show_toast(text: str, duration_ms: int = DEFAULT_DURATION_MS) -> None:
    if not text:
        return
    preview = text if len(text) <= MAX_PREVIEW_CHARS else text[: MAX_PREVIEW_CHARS - 1] + "…"

    def _build(root: tk.Tk) -> None:
        win = tk.Toplevel(root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        try:
            win.attributes("-alpha", 0.94)
        except tk.TclError:
            pass

        frame = tk.Frame(win, bg="#1f2330", padx=14, pady=10)
        frame.pack(fill="both", expand=True)

        tk.Label(
            frame,
            text="Voice Flow",
            bg="#1f2330",
            fg="#7fb1ff",
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")
        tk.Label(
            frame,
            text=preview,
            bg="#1f2330",
            fg="#e7eaf3",
            font=("Segoe UI", 10),
            wraplength=320,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        w = win.winfo_width()
        h = win.winfo_height()
        x = sw - w - 24
        y = sh - h - 80
        win.geometry(f"+{x}+{y}")

        win.after(duration_ms, win.destroy)

    get_ui().submit(_build)